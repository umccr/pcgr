#!/usr/bin/env python

import csv
import re
import argparse
import os
import subprocess
import logging
import sys
import pandas as pd
import gzip

from cyvcf2 import VCF
from pcgr import utils, annoutils, vcf
from pcgr.utils import error_message, check_subprocess, random_string, sort_bed, check_file_exists


def __main__():

    parser = argparse.ArgumentParser(description='Verify input data for CPSR')
    parser.add_argument('pcgr_dir',help='PCGR base directory with accompanying data directory')
    parser.add_argument('input_vcf', help='VCF input file with query variants (SNVs/InDels)')
    parser.add_argument('custom_target_tsv',help='Custom text/TSV file indicating user-defined target genes from panel 0 for screening and reporting')
    parser.add_argument('custom_target_bed',help='Name of BED file populated with regions associated with custom target genes defined by user')
    parser.add_argument('retained_info_tags',help='Comma-separated string of VCF INFO tags in query VCF to be retained for output')
    parser.add_argument('genome_assembly',help='grch37 or grch38')
    parser.add_argument('sample_id',help='CPSR sample_name')
    parser.add_argument('virtual_panel_id',type=str,help='virtual panel identifier(s)')
    parser.add_argument('diagnostic_grade_only', type=int, default=0, choices=[0,1], help="Green virtual panels only (Genomics England PanelApp)")
    parser.add_argument('gwas_findings', type=int, default=0, choices=[0,1], help="Include GWAS findings")
    parser.add_argument('secondary_findings', type=int, default=0, choices=[0,1], help="Include secondary findings")
    parser.add_argument('--output_dir', dest='output_dir', help='Output directory')
    parser.add_argument("--debug", action="store_true", help="Print full commands to log")
    args = parser.parse_args()

    ret = validate_cpsr_input(args.pcgr_dir,
                              args.input_vcf,
                              args.custom_target_tsv,
                              args.custom_target_bed,
                              args.retained_info_tags,
                              args.genome_assembly,
                              args.sample_id,
                              args.virtual_panel_id,
                              args.diagnostic_grade_only,
                              args.gwas_findings,
                              args.secondary_findings,
                              args.output_dir,
                              args.debug)
    if ret != 0:
       sys.exit(1)


def get_valid_custom_genelist(genelist_fname, genelist_bed_fname, pcgr_dir, genome_assembly, 
                              gwas_findings, secondary_findings, logger, debug):
    """
    Function that checks whether the custom genelist contains valid entries from the complete exploratory track
    """
    
    random_strings = [random_string(15), random_string(15), random_string(15), random_string(15)]
    
    genelist_reader = csv.DictReader(open(genelist_fname,'r'), delimiter='\n', fieldnames=['ensembl_gene_id'])
    virtualpanel_track_bed = os.path.join(
        pcgr_dir, "data", genome_assembly, "gene","bed","gene_virtual_panel", "0.bed.gz")
    virtualpanel_track_tsv = os.path.join(
        pcgr_dir, "data", genome_assembly, "gene","tsv","gene_virtual_panel", "gene_virtual_panel.tsv.gz")
    genelist_bed_fname_unsorted = f'{genelist_bed_fname}.{random_strings[0]}.unsorted.bed'

    customlist_identifiers = {}
    superpanel_track = []
    superpanel_identifiers_all = {}
    valid_custom_identifiers = []
    valid_custom_symbols = []

    for row in genelist_reader:
        if not re.match(r'^ENSG[0-9]{1,}$', str(row['ensembl_gene_id']).rstrip()):
            err_msg = "Custom list of genes from CPSR superpanel (panel 0) should be provided as Ensembl " + \
                "gene identifiers, '" + str(row['ensembl_gene_id']) + "' is not a valid identifier"
            return error_message(err_msg, logger)
        else:
            customlist_identifiers[str(row['ensembl_gene_id']).strip()] = 1

    with gzip.open(virtualpanel_track_tsv, mode='rt') as f:
        virtualpanel_reader = csv.DictReader(f, delimiter = '\t')
        for row in virtualpanel_reader:
            if row['id'] == '0':
                superpanel_track.append(dict(row))

    i = 0
    while i < len(superpanel_track):
        superpanel_identifiers_all[superpanel_track[i]['ensembl_gene_id']] = superpanel_track[i]['symbol']
        i = i + 1

    for g in customlist_identifiers.keys():
        if g in superpanel_identifiers_all.keys():
            valid_custom_identifiers.append(g)
            valid_custom_symbols.append(superpanel_identifiers_all[g])
        else:
            logger.warning("Ignoring custom-provided gene identifier (" + str(g) + ") NOT found in CPSR superpanel (panel 0)")
            logger.warning("Choose only Ensembl gene identifiers from panel 0 in this file : " + str(virtualpanel_track_tsv))
    all_valid_custom_geneset = ', '.join(sorted(valid_custom_symbols))

    logger.info('Detected n = ' + str(len(valid_custom_identifiers)) + ' valid targets in custom-provided gene list file (--custom_list)):')
    logger.info(all_valid_custom_geneset)

    if len(valid_custom_identifiers) == 0:
        logger.info('')
        logger.info("NO valid gene identifiers from panel 0 in custom-provided genelist - exiting")
        logger.info('')
        exit(1)

    ## Add custom set of genes to target BED
    logger.info('Creating BED file with custom target genes: ' + str(genelist_bed_fname))
    id_pat = '|'.join([f"\|{g}\|" for g in valid_custom_identifiers])
    
    id_pat_ext = id_pat + '|(\|tag\|)|' + '(\|ACMG_SF\|)'
    cmd_target_regions_bed = f"bgzip -dc {virtualpanel_track_bed} | egrep '{id_pat_ext}' > {genelist_bed_fname_unsorted}"
    if gwas_findings == 0 and secondary_findings == 1:
        cmd_target_regions_bed = f"bgzip -dc {virtualpanel_track_bed} | egrep '{id_pat}' | egrep -v '(\|tag\|)' > {genelist_bed_fname_unsorted}"
    if gwas_findings == 0 and secondary_findings == 0:
        cmd_target_regions_bed = f"bgzip -dc {virtualpanel_track_bed} | egrep '{id_pat}' | egrep -v '(\|tag\|)|(\ACMG_SF\|)' > {genelist_bed_fname_unsorted}"
    if gwas_findings == 1 and secondary_findings == 0:
        cmd_target_regions_bed = f"bgzip -dc {virtualpanel_track_bed} | egrep '{id_pat}' | egrep -v '(\ACMG_SF\|)' > {genelist_bed_fname_unsorted}"
    
    check_subprocess(logger, cmd_target_regions_bed, debug)
    
    ## Sort regions in target BED
    sort_bed(genelist_bed_fname_unsorted, genelist_bed_fname, debug, logger)

    return 0


def simplify_vcf(input_vcf, vcf, custom_bed, pcgr_directory, genome_assembly, virtual_panel_id, 
                 sample_id, diagnostic_grade_only, gwas_findings, secondary_findings, output_dir, logger, debug):

    """
    Function that performs four separate checks/filters on the validated input VCF:
    1. Remove/Strip off any genotype data (not needed for annotation)
    2. If VCF have variants with multiple alternative alleles ("multiallelic", e.g. 'A,T'), 
        these are decomposed into variants with a single alternative allele
    3. Filters against predisposition loci (virtual panel id or custom target) - includes secondary finding targets/GWAS-loci if set by user
    4. Final VCF file is sorted and indexed (bgzip + tabix)
    """

    random_strings = [random_string(15), random_string(15), random_string(15), random_string(15)] 

    temp_files = {}
    temp_files['tmp_vcf_1'] = \
        os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', f'.cpsr_ready.{random_strings[0]}.vcf', os.path.basename(input_vcf)))
    temp_files['tmp_vcf_2'] = \
        os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', f'.cpsr_ready.{random_strings[1]}.vcf.gz', os.path.basename(input_vcf)))
    temp_files['tmp_vcf_3'] = \
        os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', f'.cpsr_ready.{random_strings[2]}.vcf', os.path.basename(input_vcf)))
    temp_files['tmp_vcf_4'] = \
        os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)','.cpsr_ready.vcf', os.path.basename(input_vcf)))
    temp_files['tmp_vcf_5'] = \
        os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)','.cpsr_ready_target.vcf', os.path.basename(input_vcf)))
    
    tmp_vcf1 = os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', '.cpsr_ready.' + random_string(15) + '.vcf', os.path.basename(input_vcf)))
    tmp_vcf2 = os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', '.cpsr_ready.' + random_string(15) + '.vcf.gz', os.path.basename(input_vcf)))
    tmp_vcf3 = os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)', '.cpsr_ready.' + random_string(15) + '.vcf.gz', os.path.basename(input_vcf)))
    input_vcf_cpsr_ready_decomposed = os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)','.cpsr_ready.vcf', os.path.basename(input_vcf)))
    input_vcf_cpsr_ready_decomposed_target = os.path.join(output_dir, re.sub(r'(\.vcf$|\.vcf\.gz$)','.cpsr_ready_target.vcf', os.path.basename(input_vcf)))
    virtual_panels_tmp_bed = os.path.join(output_dir, "virtual_panels_all." + str(sample_id) + ".tmp.bed")
    virtual_panels_bed = os.path.join(output_dir, "virtual_panels_all." + str(sample_id) + ".bed")

    multiallelic_list = list()
    for rec in vcf:
        POS = rec.start + 1
        alt = ",".join(str(n) for n in rec.ALT)
        if len(rec.ALT) > 1:
            variant_id = f"{rec.CHROM}:{POS}_{rec.REF}->{alt}"
            multiallelic_list.append(variant_id)

    # bgzip + tabix required for sorting

    cmd_vcf1 = f'bcftools view {input_vcf} | bgzip -cf > {tmp_vcf2} && tabix -p vcf {tmp_vcf2} && ' + \
        f'bcftools sort --temp-dir {output_dir} -Oz {tmp_vcf2} > {tmp_vcf3} 2> {os.path.join(output_dir, "bcftools_1.cpsr_simplify_vcf.log")}' + \
        f' && tabix -p vcf {tmp_vcf3}'
    logger.info('Extracting variants on autosomal/sex/mito chromosomes only (1-22,X,Y, M/MT) with bcftools')
    # Keep only autosomal/sex/mito chrom (handle hg38 and hg19), sub chr prefix
    chrom_to_keep = [str(x) for x in [*range(1,23), 'X', 'Y', 'M', 'MT']]
    chrom_to_keep = ','.join([*['chr' + chrom for chrom in chrom_to_keep], *[chrom for chrom in chrom_to_keep]])
    cmd_vcf2 = f'bcftools view --regions {chrom_to_keep} {tmp_vcf3} | sed \'s/^chr//\' > {tmp_vcf1}'

    check_subprocess(logger, cmd_vcf1, debug)
    check_subprocess(logger, cmd_vcf2, debug)

    if multiallelic_list:
        logger.warning(f"There were {len(multiallelic_list)} multiallelic sites detected. Showing (up to) the first 100:")
        print('----')
        print(', '.join(multiallelic_list[:100]))
        print('----')
        logger.info('Decomposing multi-allelic sites in input VCF file using \'vt decompose\'')
        command_decompose = f'vt decompose -s {tmp_vcf1} > {input_vcf_cpsr_ready_decomposed} 2> {os.path.join(output_dir, "decompose.log")}'
        check_subprocess(logger, command_decompose, debug)
    else:
        command_copy = f'cp {tmp_vcf1} {input_vcf_cpsr_ready_decomposed}'
        check_subprocess(logger, command_copy, debug)


    if not custom_bed == 'None':
        logger.info('Limiting variant set to user-defined screening loci (custom list from panel 0)')
        if check_file_exists(custom_bed):
            target_variants_intersect_cmd = \
                "bedtools intersect -wa -u -header -a " + str(input_vcf_cpsr_ready_decomposed) + \
                " -b " + str(custom_bed) + " > " + str(input_vcf_cpsr_ready_decomposed_target)
            check_subprocess(logger, target_variants_intersect_cmd, debug)
    else:
        logger.info('Limiting variant set to cancer predisposition loci - virtual panel id(s): ' + str(virtual_panel_id))

        ## Concatenate all panel BEDs to one big virtual panel BED, sort and make unique
        panel_ids = str(virtual_panel_id).split(',')
        for pid in panel_ids:
            target_bed_gz = os.path.join(
                pcgr_directory,'data',genome_assembly, 'gene','bed','gene_virtual_panel', str(pid) + ".bed.gz")
            if diagnostic_grade_only == 1 and virtual_panel_id != "0":
                logger.info('Considering diagnostic-grade only genes in panel ' + str(pid) + ' - (GREEN status in Genomics England PanelApp)')
                target_bed_gz = os.path.join(
                    pcgr_directory, 'data', genome_assembly, 'gene','bed','gene_virtual_panel', str(pid) + ".GREEN.bed.gz")
            
            check_file_exists(target_bed_gz, logger)
            
            if gwas_findings == 0 and secondary_findings == 1:
                check_subprocess(logger, f'bgzip -dc {target_bed_gz} | egrep -v "(\|tag\|)" >> {virtual_panels_tmp_bed}', debug)
            elif gwas_findings == 0 and secondary_findings == 0:
                check_subprocess(logger, f'bgzip -dc {target_bed_gz} | egrep -v "(\|tag\|)|(\ACMG_SF\|)" >> {virtual_panels_tmp_bed}', debug)
            elif gwas_findings == 1 and secondary_findings == 0:
                check_subprocess(logger, f'bgzip -dc {target_bed_gz} | egrep -v "(\ACMG_SF\|)" >> {virtual_panels_tmp_bed}', debug)
            else:
                check_subprocess(logger, f'bgzip -dc {target_bed_gz} >> {virtual_panels_tmp_bed}', debug)

        ## sort the collection of virtual panels
        sort_bed(virtual_panels_tmp_bed, virtual_panels_bed, debug, logger)

        if check_file_exists(virtual_panels_bed):
            target_variants_intersect_cmd = f'bedtools intersect -wa -u -header -a {input_vcf_cpsr_ready_decomposed} -b ' + \
                f'{virtual_panels_bed} > {input_vcf_cpsr_ready_decomposed_target}'
            check_subprocess(logger, target_variants_intersect_cmd, debug)


    check_subprocess(logger, f'bgzip -cf {input_vcf_cpsr_ready_decomposed_target} > {input_vcf_cpsr_ready_decomposed_target}.gz', debug)
    check_subprocess(logger, f'tabix -p vcf {input_vcf_cpsr_ready_decomposed_target}.gz', debug)
    if not debug:
        for fn in [tmp_vcf1, tmp_vcf2, tmp_vcf3,  
                   virtual_panels_bed, 
                   input_vcf_cpsr_ready_decomposed, 
                   os.path.join(output_dir, "decompose.log"), 
                   os.path.join(output_dir, "bcftools_1.cpsr_simplify_vcf.log")]:
            #print(f"Deleting {fn}")
            utils.remove(fn)
        
        utils.remove(tmp_vcf2 + str('.tbi'))
        utils.remove(tmp_vcf3 + str('.tbi'))

    if check_file_exists(f'{input_vcf_cpsr_ready_decomposed_target}.gz'):
        vcf = VCF(input_vcf_cpsr_ready_decomposed_target + '.gz')
        i = 0
        for rec in vcf:
            i = i + 1
        if len(vcf.seqnames) == 0 or i == 0:
            logger.info('')
            logger.info("Query VCF contains NO variants within the selected cancer predisposition geneset (or "\
                "GWAS loci/secondary findings) - quitting workflow")
            logger.info('')
            exit(1)

def validate_cpsr_input(pcgr_directory, 
                        input_vcf, 
                        custom_list_fname, 
                        custom_list_bed_fname,
                        retained_info_tags, 
                        genome_assembly, 
                        sample_id, 
                        virtual_panel_id, 
                        diagnostic_grade_only, 
                        gwas_findings, 
                        secondary_findings, 
                        output_dir, debug):
    """
    Function that reads the input files to CPSR (VCF file + custom gene list) and performs the following checks:
    0. If custom gene list (panel) is provided, checks the validity of this list
    1. Check that no INFO annotation tags in the query VCF coincides with those generated by CPSR
    2. Check that custom VCF INFO tags set by user as retained for output is found in query VCF
    3. Check that if VCF have variants with multiple alternative alleles (e.g. 'A,T') run vt decompose
    4. The resulting VCF file is sorted and indexed (bgzip + tabix)
    """
    logger = utils.getlogger('cpsr-validate-input-arguments')

    custom_target_fname = {}
    custom_target_fname['tsv'] = custom_list_fname

    custom_target_fname['bed'] = 'None'
    if not custom_target_fname['tsv'] == 'None':
        logger.info('Establishing BED track with custom list of genes from panel 0')
        custom_target_fname['bed'] = custom_list_bed_fname
        get_valid_custom_genelist(custom_target_fname['tsv'], 
                                  custom_target_fname['bed'], 
                                  pcgr_directory, 
                                  genome_assembly, 
                                  gwas_findings, 
                                  secondary_findings, 
                                  logger, 
                                  debug)

    if not input_vcf == 'None':
        
        vcf_object = VCF(input_vcf)
        
        ## Check that VCF does not contain INFO tags that will be appended with PCGR annotation
        populated_infotags_other_fname = os.path.join(pcgr_directory,'data',genome_assembly, 'vcf_infotags_other.tsv')
        populated_infotags_vep_fname = os.path.join(pcgr_directory,'data',genome_assembly, 'vcf_infotags_vep.tsv')
        tags_cpsr = annoutils.read_infotag_file(populated_infotags_other_fname, scope = "cpsr")
        tags_vep = annoutils.read_infotag_file(populated_infotags_vep_fname, scope = "vep")
        tags_cpsr.update(tags_vep)
        tag_check = vcf.check_existing_vcf_info_tags(vcf_object, tags_cpsr, logger)
        if tag_check == -1:
            return -1        

        if retained_info_tags != "None":
            custom_check = vcf.check_retained_vcf_info_tags(vcf_object, retained_info_tags, logger)
            if custom_check == -1:
                return -1

        samples = vcf_object.samples
        if len(samples) > 1:
            err_msg = "Query VCF contains more than one sample column (" + ', '.join(samples) + ") - " + \
                "CPSR expects a germline VCF with a single sample column - exiting"
            return error_message(err_msg, logger)
        
        simplify_vcf(input_vcf, 
                     vcf_object, 
                     custom_target_fname['bed'], 
                     pcgr_directory, 
                     genome_assembly, 
                     virtual_panel_id, 
                     sample_id, 
                     diagnostic_grade_only, 
                     gwas_findings, 
                     secondary_findings, 
                     output_dir, 
                     logger, 
                     debug)

    return 0

if __name__=="__main__":
    __main__()
