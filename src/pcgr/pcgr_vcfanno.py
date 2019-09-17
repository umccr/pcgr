#!/usr/bin/env python

import argparse
from cyvcf2 import VCF
import random
import annoutils
import os
import re
import sys

logger = annoutils.getlogger('pcgr-vcfanno')


def __main__():
   parser = argparse.ArgumentParser(description='Run brentp/vcfanno - annotate a VCF file against multiple VCF files in parallel', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
   parser.add_argument('query_vcf', help='Bgzipped input VCF file with query variants (SNVs/InDels)')
   parser.add_argument('out_vcf', help='Output VCF file with appended annotations from multiple VCF files')
   parser.add_argument('pcgr_db_dir', help='PCGR assembly-specific data directory')
   parser.add_argument('--num_processes', help="Number of processes vcfanno can use during annotation", default=4)
   parser.add_argument("--docm",action = "store_true", help="Annotate VCF with annotations from Database of Curated Mutations")
   parser.add_argument("--intogen_driver_mut",action = "store_true", help="Annotate VCF with predicted cancer driver mutations from IntoGen's Catalog of Driver Mutations")
   parser.add_argument("--clinvar",action = "store_true", help="Annotate VCF with annotations from ClinVar")
   parser.add_argument("--dbnsfp",action = "store_true", help="Annotate VCF with annotations from database of non-synonymous functional predictions")
   parser.add_argument("--tcga",action = "store_true", help="Annotate VCF with variant frequencies from the The Cancer Genome Atlas")
   parser.add_argument("--tcga_pcdm",action = "store_true", help="Annotate VCF with putative cancer driver mutations from The Cancer Genome Atlas")
   parser.add_argument("--chasmplus", action="store_true",help="Annotate VCF with putative cancer driver mutations from CHASMplus algorithm")
   parser.add_argument("--civic",action = "store_true", help="Annotate VCF with annotations from the Clinical Interpretation of Variants in Cancer database")
   parser.add_argument("--cbmdb",action = "store_true", help="Annotate VCF with annotations from the Cancer bioMarkers database")
   parser.add_argument("--icgc",action = "store_true", help="Annotate VCF with known variants found in the ICGC-PCAWG sequencing project")
   parser.add_argument("--cancer_hotspots",action = "store_true", help="Annotate VCF with mutation hotspots from cancerhotspots.org")
   parser.add_argument("--uniprot",action = "store_true", help="Annotate VCF with protein functional features from the UniProt Knowledgebase")
   parser.add_argument("--pcgr_onco_xref",action = "store_true", help="Annotate VCF with transcript annotations from PCGR (targeted drugs, protein complexes, cancer gene associations, etc)")
   parser.add_argument("--gwas",action = "store_true", help="Annotate VCF against known loci associated with cancer, as identified from genome-wide association studies (GWAS)")
   parser.add_argument("--rmsk",action = "store_true", help="Annotate VCF against known sequence repeats, as identified by RepeatMasker (rmsk)")
   parser.add_argument("--simplerepeats",action = "store_true", help="Annotate VCF against known sequence repeats, as identified by Tandem Repeats Finder (simplerepeats)")
   parser.add_argument("--winmsk",action = "store_true", help="Annotate VCF against known sequence repeats, as identified by Windowmasker (winmsk)")
   parser.add_argument("--gnomad_cpsr",action = "store_true",help="Annotate VCF with population-specific allelic counts and frequencies in cancer predisposition genes (gnomAD non-cancer subset)")
   parser.add_argument("--panel_normal_vcf",dest="panel_normal_vcf",help="Annotate VCF with germline calls from panel of normals")

   args = parser.parse_args()
   query_info_tags = get_vcf_info_tags(args.query_vcf)
   vcfheader_file = args.out_vcf + '.tmp.' + str(random.randrange(0,10000000)) + '.header.txt'
   conf_fname = args.out_vcf + '.tmp.conf.toml'
   print_vcf_header(args.query_vcf, vcfheader_file, chromline_only = False)
   run_vcfanno(args.num_processes, args.query_vcf, args.panel_normal_vcf, query_info_tags, vcfheader_file, args.pcgr_db_dir, conf_fname, args.out_vcf, args.docm, args.intogen_driver_mut, args.clinvar, args.tcga, args.tcga_pcdm, args.chasmplus, args.dbnsfp, args.civic, args.cbmdb, args.icgc, args.uniprot, args.cancer_hotspots, args.pcgr_onco_xref, args.gwas, args.rmsk, args.simplerepeats, args.winmsk, args.gnomad_cpsr)


def prepare_vcfanno_configuration(vcfanno_data_directory, conf_fname, vcfheader_file, logger, datasource_info_tags, query_info_tags, datasource):
   for t in datasource_info_tags:
      if t in query_info_tags:
         logger.warning("Query VCF has INFO tag " + str(t) + ' - this is also present in the ' + str(datasource) + ' VCF/BED annotation file. This tag will be overwritten if not renamed in the query VCF')
   append_to_conf_file(datasource, datasource_info_tags, vcfanno_data_directory, conf_fname)
   append_to_vcf_header(vcfanno_data_directory, datasource, vcfheader_file)

def run_vcfanno(num_processes, query_vcf, panel_normal_vcf, query_info_tags, vcfheader_file, pcgr_db_directory, conf_fname, output_vcf, docm, intogen_driver_mut, clinvar, tcga, tcga_pcdm, chasmplus, dbnsfp, civic, cbmdb, icgc, uniprot, cancer_hotspots, pcgr_onco_xref, gwas, rmsk, simplerepeats, winmsk, gnomad_cpsr):
   """
   Function that annotates a VCF file with vcfanno against a user-defined set of germline and somatic VCF files
   """
   
   civic_info_tags = ["CIVIC_ID","CIVIC_ID_2"]
   cbmdb_info_tags = ["CBMDB_ID"]
   icgc_info_tags = ["ICGC_PCAWG_OCCURRENCE","ICGC_PCAWG_AFFECTED_DONORS"]
   docm_info_tags = ["DOCM_PMID"]
   tcga_info_tags = ["TCGA_FREQUENCY","TCGA_PANCANCER_COUNT"]
   tcga_pcdm_info_tags = ["PUTATIVE_DRIVER_MUTATION"]
   chasmplus_info_tags = ["CHASMPLUS_DRIVER","CHASMPLUS_TTYPE","CHASMPLUS_PANCAN"]
   intogen_driver_mut_info_tags = ["INTOGEN_DRIVER_MUT"]
   clinvar_info_tags = ["CLINVAR_MSID","CLINVAR_PMID","CLINVAR_CLNSIG","CLINVAR_VARIANT_ORIGIN","CLINVAR_CONFLICTED","CLINVAR_MEDGEN_CUI",
                        "CLINVAR_MEDGEN_CUI_SOMATIC","CLINVAR_CLNSIG_SOMATIC","CLINVAR_PMID_SOMATIC","CLINVAR_ALLELE_ID","CLINVAR_HGVSP",
                        "CLINVAR_REVIEW_STATUS_STARS","CLINVAR_CLASSIFICATION","CLINVAR_ENTREZGENE"]
   cancer_hotspots_info_tags = ["MUTATION_HOTSPOT","MUTATION_HOTSPOT_TRANSCRIPT","MUTATION_HOTSPOT_CANCERTYPE"]
   dbnsfp_info_tags = ["DBNSFP"]
   uniprot_info_tags = ["UNIPROT_FEATURE"]
   pcgr_onco_xref_info_tags = ["PCGR_ONCO_XREF"]
   gwas_info_tags = ["GWAS_HIT"]
   rmsk_info_tags = ["RMSK_HIT"]
   simplerepeats_info_tags = ["SIMPLEREPEATS_HIT"]
   winmsk_info_tags = ["WINMASKER_HIT"]
   panel_normal_tags = ["PANEL_OF_NORMALS"]

   gnomad_cpsr_tags = []
   gnomad_cpsr_tags.append('NON_CANCER_AC_GLOBAL')
   gnomad_cpsr_tags.append('NON_CANCER_NHOMALT_GLOBAL')
   gnomad_cpsr_tags.append('NON_CANCER_AN_GLOBAL')
   gnomad_cpsr_tags.append('NON_CANCER_AF_GLOBAL')
   for pop in ['ASJ','NFE','SAS','FIN','EAS','AMR','AFR','OTH']:
      gnomad_cpsr_tags.append('NON_CANCER_AC_' + str(pop))
      gnomad_cpsr_tags.append('NON_CANCER_AN_' + str(pop))
      gnomad_cpsr_tags.append('NON_CANCER_AF_' + str(pop))
      gnomad_cpsr_tags.append('NON_CANCER_NHOMALT_' + str(pop))
      
   if icgc is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, icgc_info_tags, query_info_tags, "icgc")
   if clinvar is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, clinvar_info_tags, query_info_tags, "clinvar")
   if dbnsfp is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, dbnsfp_info_tags, query_info_tags, "dbnsfp")
   if cbmdb is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, cbmdb_info_tags, query_info_tags, "cbmdb")
   if tcga is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, tcga_info_tags, query_info_tags, "tcga")
   if tcga_pcdm is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, tcga_pcdm_info_tags, query_info_tags, "tcga_pcdm")
   if chasmplus is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, chasmplus_info_tags, query_info_tags, "chasmplus")
   if civic is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, civic_info_tags, query_info_tags, "civic")
   if cancer_hotspots is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, cancer_hotspots_info_tags, query_info_tags, "cancer_hotspots")
   if uniprot is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, uniprot_info_tags, query_info_tags, "uniprot")
   if docm is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, docm_info_tags, query_info_tags, "docm")
   if intogen_driver_mut is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, intogen_driver_mut_info_tags, query_info_tags, "intogen_driver_mut")
   if pcgr_onco_xref is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, pcgr_onco_xref_info_tags, query_info_tags, "pcgr_onco_xref")
   if gwas is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, gwas_info_tags, query_info_tags, "gwas")
   if rmsk is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, rmsk_info_tags, query_info_tags, "rmsk")
   if simplerepeats is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, simplerepeats_info_tags, query_info_tags, "simplerepeats")
   if winmsk is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, winmsk_info_tags, query_info_tags, "winmsk")
   if gnomad_cpsr is True:
      prepare_vcfanno_configuration(pcgr_db_directory, conf_fname, vcfheader_file, logger, gnomad_cpsr_tags, query_info_tags, "gnomad_cpsr")
   
   if not panel_normal_vcf is None:
      if "PANEL_OF_NORMALS" in query_info_tags:
         logger.warning("Query VCF has INFO tag \"PANEL_OF_NORMALS\" - this is also present in the panel of normal VCF file. This tag will be overwritten if not renamed in the query VCF")
      append_to_vcf_header(pcgr_db_directory, "panel_of_normals", vcfheader_file)
      fh = open(conf_fname,'a')
      fh.write('[[annotation]]\n')
      fh.write('file="' + str(panel_normal_vcf) + '"\n')
      fields_string = 'fields = ["' + '","'.join(panel_normal_tags) + '"]'
      ops = ['self'] * len(panel_normal_tags)
      ops_string = 'ops=["' + '","'.join(ops) + '"]'
      fh.write(fields_string + '\n')
      fh.write(ops_string + '\n\n')
      fh.close()


   out_vcf_vcfanno_unsorted1 = output_vcf + '.tmp.unsorted.1'
   query_prefix = re.sub(r'\.vcf.gz$','',query_vcf)
   print_vcf_header(query_vcf, vcfheader_file, chromline_only = True)
   command1 = "vcfanno -p=" + str(num_processes) + " " + str(conf_fname) + " " + str(query_vcf) + " > " + str(out_vcf_vcfanno_unsorted1) + " 2> " + str(query_prefix) + '.vcfanno.log'
   os.system(command1)
   
   os.system('cat ' + str(vcfheader_file) + ' > ' + str(output_vcf))
   os.system('cat ' + str(out_vcf_vcfanno_unsorted1) + ' | grep -v \'^#\' >> ' + str(output_vcf))
   os.system('rm -f ' + str(output_vcf) + '.tmp*')
   os.system('bgzip -f ' + str(output_vcf))
   os.system('tabix -f -p vcf ' + str(output_vcf) + '.gz')
   return 0
   
def append_to_vcf_header(pcgr_db_directory, datasource, vcfheader_file):
   """
   Function that appends the VCF header information for a given 'datasource' (containing INFO tag formats/descriptions, and datasource version)
   """
   vcf_info_tags_file = str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.vcfanno.vcf_info_tags.txt'
   os.system('cat ' + str(vcf_info_tags_file) + ' >> ' + str(vcfheader_file))


def append_to_conf_file(datasource, datasource_info_tags, pcgr_db_directory, conf_fname):
   """
   Function that appends data to a vcfanno conf file ('conf_fname') according to user-defined ('datasource'). The datasource defines the set of tags that will be appended during annotation
   """
   fh = open(conf_fname,'a')
   if datasource != 'civic' and datasource != 'uniprot' and datasource != 'pcgr_onco_xref' and datasource != 'rmsk' and datasource != 'winmsk' and datasource != 'simplerepeats':
      fh.write('[[annotation]]\n')
      fh.write('file="' + str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.vcf.gz"\n')
      fields_string = 'fields = ["' + '","'.join(datasource_info_tags) + '"]'
      ops = ['concat'] * len(datasource_info_tags)
      ops_string = 'ops=["' + '","'.join(ops) + '"]'
      fh.write(fields_string + '\n')
      fh.write(ops_string + '\n\n')
   else:
      if datasource == 'uniprot' or datasource == 'pcgr_onco_xref' or datasource == 'rmsk':
         fh.write('[[annotation]]\n')
         fh.write('file="' + str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.bed.gz"\n')
         fh.write('columns=[4]\n')
         names_string = 'names=["' + '","'.join(datasource_info_tags) + '"]'
         fh.write(names_string +'\n')
         fh.write('ops=["concat"]\n\n')
      if datasource == 'simplerepeats' or datasource == 'winmsk':
         fh.write('[[annotation]]\n')
         fh.write('file="' + str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.bed.gz"\n')
         fh.write('columns=[4]\n')
         names_string = 'names=["' + '","'.join(datasource_info_tags) + '"]'
         fh.write(names_string +'\n')
         fh.write('ops=["flag"]\n\n')
      if datasource == 'civic':
         fh.write('[[annotation]]\n')
         fh.write('file="' + str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.bed.gz"\n')
         fh.write('columns=[4]\n')
         fh.write('names=["CIVIC_ID_2"]\n')
         fh.write('ops=["concat"]\n\n')

         fh.write('[[annotation]]\n')
         fh.write('file="' + str(pcgr_db_directory) + '/' + str(datasource) + '/' + str(datasource) + '.vcf.gz"\n')
         fh.write('fields = ["CIVIC_ID"]\n')
         fh.write('ops=["concat"]\n\n')
   fh.close()
   return

def get_vcf_info_tags(vcffile):
   vcf = VCF(vcffile)
   info_tags = {}
   for e in vcf.header_iter():
      header_element = e.info()
      if 'ID' in header_element.keys() and 'HeaderType' in header_element.keys():
         if header_element['HeaderType'] == 'INFO':
            info_tags[str(header_element['ID'])] = 1
   
   return info_tags


def print_vcf_header(query_vcf, vcfheader_file, chromline_only = False):
   if chromline_only == True:
      os.system('bgzip -dc ' + str(query_vcf) + ' | egrep \'^#\' | egrep \'^#CHROM\' >> ' + str(vcfheader_file))
   else:
      os.system('bgzip -dc ' + str(query_vcf) + ' | egrep \'^#\' | egrep -v \'^#CHROM\' > ' + str(vcfheader_file))

if __name__=="__main__": __main__()
