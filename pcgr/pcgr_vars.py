#!/usr/bin/env python

from pcgr._version import __version__

PCGR_VERSION = __version__
DB_VERSION = '20231212'

## MISCELLANEOUS
NCBI_BUILD_MAF = 'GRCh38'
MAX_VARIANTS_FOR_REPORT = 500_000
CODING_EXOME_SIZE_MB = 34.0
RECOMMENDED_N_MUT_SIGNATURE = 200

## GENCODE
GENCODE_VERSION = {'grch38': 44,'grch37': 19}

## vcfanno
VCFANNO_MAX_PROC = 15

## VEP settings/versions
VEP_VERSION = '110'
VEP_ASSEMBLY = {'grch38': 'GRCh38','grch37': 'GRCh37'}
VEP_MIN_FORKS = 1
VEP_MAX_FORKS = 8
VEP_MIN_BUFFER_SIZE = 50
VEP_MAX_BUFFER_SIZE = 30000
VEP_PICK_CRITERIA = ['mane','canonical','appris','tsl','biotype','ccds','rank','length']

tsites = {
    0: 'Any',
    1: 'Adrenal Gland',
    2: 'Ampulla of Vater',
    3: 'Biliary Tract',
    4: 'Bladder/Urinary Tract',
    5: 'Bone',
    6: 'Breast',
    7: 'Cervix',
    8: 'CNS/Brain',
    9: 'Colon/Rectum',
    10: 'Esophagus/Stomach',
    11: 'Eye',
    12: 'Head and Neck',
    13: 'Kidney',
    14: 'Liver',
    15: 'Lung',
    16: 'Lymphoid',
    17: 'Myeloid',
    18: 'Ovary/Fallopian Tube',
    19: 'Pancreas',
    20: 'Peripheral Nervous System',
    21: 'Peritoneum',
    22: 'Pleura',
    23: 'Prostate',
    24: 'Skin',
    25: 'Soft Tissue',
    26: 'Testis',
    27: 'Thymus',
    28: 'Thyroid',
    29: 'Uterus',
    30: 'Vulva/Vagina'
}

tumor_sites = '\n'.join([f'{k} = {tsites[k]}' for k in tsites]) # for displaying in help

GE_panels = {
      0: "CPSR exploratory cancer predisposition panel (PanelApp genes / TCGA's germline study / Cancer Gene Census / Other)",
      1: "Adult solid tumours cancer susceptibility (GEP)",
      2: "Adult solid tumours for rare disease (GEP)",
      3: "Bladder cancer pertinent cancer susceptibility (GEP)",
      4: "Brain cancer pertinent cancer susceptibility (GEP)",
      5: "Breast cancer pertinent cancer susceptibility (GEP)",
      6: "Childhood solid tumours cancer susceptibility (GEP)",
      7: "Colorectal cancer pertinent cancer susceptibility (GEP)",
      8: "Endometrial cancer pertinent cancer susceptibility (GEP)",
      9: "Familial Tumours Syndromes of the central & peripheral Nervous system (GEP)",
      10: "Familial breast cancer (GEP)",
      11: "Familial melanoma (GEP)",
      12: "Familial prostate cancer (GEP)",
      13: "Familial rhabdomyosarcoma (GEP)",
      14: "GI tract tumours (GEP)",
      15: "Genodermatoses with malignancies (GEP)",
      16: "Haematological malignancies cancer susceptibility (GEP)",
      17: "Haematological malignancies for rare disease (GEP)",
      18: "Head and neck cancer pertinent cancer susceptibility (GEP)",
      19: "Inherited MMR deficiency (Lynch Syndrome) - GEP",
      20: "Inherited non-medullary thyroid cancer (GEP)",
      21: "Inherited ovarian cancer (without breast cancer) (GEP)",
      22: "Inherited pancreatic cancer (GEP)",
      23: "Inherited polyposis and early onset colorectal cancer (GEP)",
      24: "Inherited predisposition to acute myeloid leukaemia (AML) (GEP)",
      25: "Inherited susceptibility to acute lymphoblastoid leukaemia (ALL) (GEP)",
      26: "Inherited predisposition to GIST (GEP)",
      27: "Inherited renal cancer (GEP)",
      28: "Inherited phaeochromocytoma and paraganglioma (GEP)",
      29: "Melanoma pertinent cancer susceptibility (GEP)",
      30: "Multiple endocrine tumours (GEP)",
      31: "Multiple monogenic benign skin tumours (GEP)",
      32: "Neuroendocrine cancer pertinent cancer susceptibility (GEP)",
      33: "Neurofibromatosis Type 1 (GEP)",
      34: "Ovarian cancer pertinent cancer susceptibility (GEP)",
      35: "Parathyroid Cancer (GEP)",
      36: "Prostate cancer pertinent cancer susceptibility (GEP)",
      37: "Renal cancer pertinent cancer susceptibility (GEP)",
      38: "Rhabdoid tumour predisposition (GEP)",
      39: "Sarcoma cancer susceptibility (GEP)",
      40: "Sarcoma susceptbility (GEP)",
      41: "Thyroid cancer pertinent cancer susceptibility (GEP)",
      42: "Tumour predisposition - childhood onset (GEP)",
      43: "Upper gastrointestinal cancer pertinent cancer susceptibility (GEP)",
      44: "DNA repair genes pertinent cancer susceptibility (GEP)"
}

panels = '\n'.join([f'{k} = {GE_panels[k]}' for k in GE_panels]) # for displaying in help

## https://www.ensembl.org/info/genome/variation/prediction/predicted_data.html#consequences
VEP_consequence_rank = {
    'transcript_ablation': 1,
    'splice_acceptor_variant': 2,
    'splice_donor_variant': 3,
    'stop_gained': 4,
    'frameshift_variant': 5,
    'stop_lost': 6,
    'start_lost' : 7,
    'transcript_amplification': 8,
    'feature_elongation': 9,
    'feature_truncation': 10,
    'inframe_insertion': 11,
    'inframe_deletion': 12,
    'missense_variant': 13,
    'protein_altering_variant': 14,
    'splice_donor_5th_base_variant': 15,
    'splice_region_variant': 16,
    'splice_donor_region_variant': 17,
    'splice_polypyrimidine_tract_variant': 18,
    'incomplete_terminal_codon_variant': 19,
    'start_retained_variant': 20,
    'stop_retained_variant': 21,
    'synonymous_variant': 22,
    'coding_sequence_variant': 23,
    'mature_miRNA_variant': 24,
    '5_prime_UTR_variant': 25,
    '3_prime_UTR_variant': 26,
    'non_coding_transcript_exon_variant': 27,
    'intron_variant': 28,
    'NMD_transcript_variant': 29,
    'non_coding_transcript_variant': 30,
    'coding_transcript_variant': 31,
    'upstream_gene_variant': 32,
    'downstream_gene_variant': 33,
    'TFBS_ablation': 34,
    'TFBS_amplification': 35,
    'TF_binding_site_variant': 36,
    'regulatory_region_ablation': 37,
    'regulatory_region_amplification': 38,
    'regulatory_region_variant': 39,
    'intergenic_variant': 40,
    'sequence_variant': 41
}

CSQ_MISSENSE_PATTERN = r"^missense_variant"
CSQ_CODING_PATTERN = r"^(stop_(lost|gained)|start_lost|frameshift_|missense_|splice_(donor|acceptor)|protein_altering|inframe_)"
CSQ_CODING_SILENT_PATTERN = r"^(stop_(lost|gained)|start_lost|frameshift_|missense_|splice_(donor|acceptor)|protein_altering|inframe_|synonymous|(start|stop)_retained)"
CSQ_NULL_PATTERN = r"^(stop_gained|frameshift_)"
CSQ_SPLICE_REGION_PATTERN = r"^(splice_|intron_variant)"
CSQ_SPLICE_DONOR_PATTERN = r"^(splice_region_variant|splice_donor_variant|splice_donor_region_variant|splice_donor_5th_base_variant)"

