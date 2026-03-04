// ============================================================
// InHealth Chronic Care - Hospital Seed Data
// 20 major US hospitals with real coordinates and capabilities
// ============================================================

CREATE (:Hospital {
    id: "mayo-clinic-rochester",
    name: "Mayo Clinic",
    short_name: "Mayo Rochester",
    city: "Rochester",
    state: "MN",
    zip: "55905",
    address: "200 First Street SW",
    lat: 44.0225,
    lon: -92.4667,
    phone: "507-284-2511",
    website: "https://www.mayoclinic.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1265,
    magnet_status: true,
    us_news_ranking: 1,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "copd_center", "diabetes_center", "ckd_advanced_care"],
    accreditations: ["The Joint Commission", "DNV Healthcare"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "cleveland-clinic",
    name: "Cleveland Clinic",
    short_name: "Cleveland Clinic",
    city: "Cleveland",
    state: "OH",
    zip: "44195",
    address: "9500 Euclid Avenue",
    lat: 41.5027,
    lon: -81.6205,
    phone: "216-444-2200",
    website: "https://my.clevelandclinic.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1400,
    magnet_status: true,
    us_news_ranking: 2,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "heart_failure_clinic", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "johns-hopkins",
    name: "Johns Hopkins Hospital",
    short_name: "Johns Hopkins",
    city: "Baltimore",
    state: "MD",
    zip: "21287",
    address: "1800 Orleans Street",
    lat: 39.2967,
    lon: -76.5928,
    phone: "443-997-9000",
    website: "https://www.hopkinsmedicine.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1162,
    magnet_status: true,
    us_news_ranking: 3,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "pediatric_specialty", "copd_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "mass-general",
    name: "Massachusetts General Hospital",
    short_name: "Mass General",
    city: "Boston",
    state: "MA",
    zip: "02114",
    address: "55 Fruit Street",
    lat: 42.3634,
    lon: -71.0688,
    phone: "617-726-2000",
    website: "https://www.massgeneral.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1057,
    magnet_status: true,
    us_news_ranking: 4,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center", "ckd_advanced_care"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "ucsf-medical-center",
    name: "UCSF Medical Center",
    short_name: "UCSF",
    city: "San Francisco",
    state: "CA",
    zip: "94143",
    address: "505 Parnassus Avenue",
    lat: 37.7631,
    lon: -122.4584,
    phone: "415-476-1000",
    website: "https://www.ucsfhealth.org",
    hospital_type: "Academic Medical Center",
    bed_count: 839,
    magnet_status: true,
    us_news_ranking: 5,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_2", "transplant", "cancer_center", "neurosurgery", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "APeX (Epic)"
});

CREATE (:Hospital {
    id: "cedars-sinai",
    name: "Cedars-Sinai Medical Center",
    short_name: "Cedars-Sinai",
    city: "Los Angeles",
    state: "CA",
    zip: "90048",
    address: "8700 Beverly Boulevard",
    lat: 34.0750,
    lon: -118.3803,
    phone: "310-423-3277",
    website: "https://www.cedars-sinai.org",
    hospital_type: "Academic Medical Center",
    bed_count: 886,
    magnet_status: true,
    us_news_ranking: 6,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "heart_failure_clinic"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "new-york-presbyterian-columbia",
    name: "New York-Presbyterian/Columbia University Irving Medical Center",
    short_name: "NYP-Columbia",
    city: "New York",
    state: "NY",
    zip: "10032",
    address: "622 West 168th Street",
    lat: 40.8402,
    lon: -73.9440,
    phone: "212-305-2500",
    website: "https://www.nyp.org",
    hospital_type: "Academic Medical Center",
    bed_count: 2478,
    magnet_status: true,
    us_news_ranking: 7,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "ventricular_assist", "pediatric_specialty"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Allscripts/Epic"
});

CREATE (:Hospital {
    id: "northwestern-memorial",
    name: "Northwestern Memorial Hospital",
    short_name: "Northwestern Memorial",
    city: "Chicago",
    state: "IL",
    zip: "60611",
    address: "251 E Huron Street",
    lat: 41.8951,
    lon: -87.6218,
    phone: "312-926-2000",
    website: "https://www.nm.org",
    hospital_type: "Academic Medical Center",
    bed_count: 921,
    magnet_status: true,
    us_news_ranking: 10,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center", "heart_failure_clinic"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "mount-sinai",
    name: "Mount Sinai Hospital",
    short_name: "Mount Sinai",
    city: "New York",
    state: "NY",
    zip: "10029",
    address: "1 Gustave L. Levy Place",
    lat: 40.7900,
    lon: -73.9520,
    phone: "212-241-6500",
    website: "https://www.mountsinai.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1228,
    magnet_status: true,
    us_news_ranking: 11,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "university-michigan",
    name: "University of Michigan Health",
    short_name: "U of M Health",
    city: "Ann Arbor",
    state: "MI",
    zip: "48109",
    address: "1500 E Medical Center Drive",
    lat: 42.2844,
    lon: -83.7268,
    phone: "734-936-4000",
    website: "https://www.uofmhealth.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1000,
    magnet_status: true,
    us_news_ranking: 12,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "copd_center", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "duke-university-hospital",
    name: "Duke University Hospital",
    short_name: "Duke University Hospital",
    city: "Durham",
    state: "NC",
    zip: "27710",
    address: "2301 Erwin Road",
    lat: 35.9949,
    lon: -78.9386,
    phone: "919-684-8111",
    website: "https://www.dukehealth.org",
    hospital_type: "Academic Medical Center",
    bed_count: 957,
    magnet_status: true,
    us_news_ranking: 14,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "unc-medical-center",
    name: "UNC Medical Center",
    short_name: "UNC Medical Center",
    city: "Chapel Hill",
    state: "NC",
    zip: "27514",
    address: "101 Manning Drive",
    lat: 35.9048,
    lon: -79.0513,
    phone: "984-974-1000",
    website: "https://www.unchealthcare.org",
    hospital_type: "Academic Medical Center",
    bed_count: 876,
    magnet_status: true,
    us_news_ranking: 18,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "diabetes_center", "ckd_advanced_care"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "vanderbilt-university-medical-center",
    name: "Vanderbilt University Medical Center",
    short_name: "Vanderbilt Medical",
    city: "Nashville",
    state: "TN",
    zip: "37232",
    address: "1211 Medical Center Drive",
    lat: 36.1434,
    lon: -86.8027,
    phone: "615-322-5000",
    website: "https://www.vumc.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1039,
    magnet_status: true,
    us_news_ranking: 19,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "ohio-state-wexner",
    name: "Ohio State University Wexner Medical Center",
    short_name: "OSU Wexner",
    city: "Columbus",
    state: "OH",
    zip: "43210",
    address: "370 W 9th Avenue",
    lat: 39.9990,
    lon: -83.0189,
    phone: "614-293-8000",
    website: "https://wexnermedical.osu.edu",
    hospital_type: "Academic Medical Center",
    bed_count: 1414,
    magnet_status: true,
    us_news_ranking: 23,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "heart_failure_clinic"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "mayo-clinic-arizona",
    name: "Mayo Clinic Arizona",
    short_name: "Mayo Arizona",
    city: "Phoenix",
    state: "AZ",
    zip: "85054",
    address: "5777 E Mayo Blvd",
    lat: 33.6601,
    lon: -111.9790,
    phone: "480-515-6296",
    website: "https://www.mayoclinic.org/patient-visitor-guide/arizona",
    hospital_type: "Academic Medical Center",
    bed_count: 280,
    magnet_status: true,
    us_news_ranking: 25,
    capabilities: ["cardiac_cath_lab", "stroke_center", "transplant", "cancer_center", "neurosurgery", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "university-chicago-medical-center",
    name: "University of Chicago Medical Center",
    short_name: "UChicago Medicine",
    city: "Chicago",
    state: "IL",
    zip: "60637",
    address: "5841 S Maryland Avenue",
    lat: 41.7890,
    lon: -87.6060,
    phone: "888-824-0200",
    website: "https://www.uchicagomedicine.org",
    hospital_type: "Academic Medical Center",
    bed_count: 811,
    magnet_status: true,
    us_news_ranking: 28,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "diabetes_center", "ckd_advanced_care"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "uc-san-diego-health",
    name: "UC San Diego Health",
    short_name: "UCSD Health",
    city: "San Diego",
    state: "CA",
    zip: "92103",
    address: "200 West Arbor Drive",
    lat: 32.7419,
    lon: -117.1547,
    phone: "619-543-6222",
    website: "https://health.ucsd.edu",
    hospital_type: "Academic Medical Center",
    bed_count: 780,
    magnet_status: true,
    us_news_ranking: 29,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "houston-methodist-hospital",
    name: "Houston Methodist Hospital",
    short_name: "Houston Methodist",
    city: "Houston",
    state: "TX",
    zip: "77030",
    address: "6565 Fannin Street",
    lat: 29.7105,
    lon: -95.3993,
    phone: "713-790-3311",
    website: "https://www.houstonmethodist.org",
    hospital_type: "Academic Medical Center",
    bed_count: 890,
    magnet_status: true,
    us_news_ranking: 22,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_2", "transplant", "cancer_center", "neurosurgery", "lvad_program", "heart_failure_clinic"],
    accreditations: ["The Joint Commission", "DNV Healthcare"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "barnes-jewish-hospital",
    name: "Barnes-Jewish Hospital",
    short_name: "Barnes-Jewish",
    city: "St. Louis",
    state: "MO",
    zip: "63110",
    address: "1 Barnes Jewish Hospital Plaza",
    lat: 38.6337,
    lon: -90.2625,
    phone: "314-747-3000",
    website: "https://www.barnesjewish.org",
    hospital_type: "Academic Medical Center",
    bed_count: 1368,
    magnet_status: true,
    us_news_ranking: 16,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_1", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

CREATE (:Hospital {
    id: "brigham-womens-hospital",
    name: "Brigham and Women's Hospital",
    short_name: "Brigham & Women's",
    city: "Boston",
    state: "MA",
    zip: "02115",
    address: "75 Francis Street",
    lat: 42.3354,
    lon: -71.1069,
    phone: "617-732-5500",
    website: "https://www.brighamandwomens.org",
    hospital_type: "Academic Medical Center",
    bed_count: 793,
    magnet_status: true,
    us_news_ranking: 8,
    capabilities: ["cardiac_cath_lab", "stroke_center", "trauma_level_2", "transplant", "cancer_center", "neurosurgery", "lvad_program", "diabetes_center", "heart_failure_clinic", "copd_center"],
    accreditations: ["The Joint Commission"],
    ehr_system: "Epic"
});

// ============================================================
// Hospital Specialty Relationships
// ============================================================

// Link hospitals to the diseases they specialize in treating
MATCH (h:Hospital {id: "mayo-clinic-rochester"}), (d:Disease {icd10: "E11.9"})
MERGE (h)-[:SPECIALIZES_IN {program: "Mayo Clinic Diabetes Center", accreditation: "ADA Education Program"}]->(d);

MATCH (h:Hospital {id: "cleveland-clinic"}), (d:Disease {icd10: "I50.9"})
MERGE (h)-[:SPECIALIZES_IN {program: "Cleveland Clinic Heart Failure Program", ranking: "Best in Nation"}]->(d);

MATCH (h:Hospital {id: "johns-hopkins"}), (d:Disease {icd10: "N18.3"})
MERGE (h)-[:SPECIALIZES_IN {program: "Johns Hopkins Comprehensive Transplant Center"}]->(d);

MATCH (h:Hospital {id: "mass-general"}), (d:Disease {icd10: "I25.10"})
MERGE (h)-[:SPECIALIZES_IN {program: "MGH Heart Center", accreditation: "ACC Chest Pain Center"}]->(d);

MATCH (h:Hospital {id: "brigham-womens-hospital"}), (d:Disease {icd10: "J44.1"})
MERGE (h)-[:SPECIALIZES_IN {program: "Brigham COPD Center", accreditation: "ATS Guidelines Center"}]->(d);

MATCH (h:Hospital {id: "northwestern-memorial"}), (d:Disease {icd10: "I48.91"})
MERGE (h)-[:SPECIALIZES_IN {program: "Bluhm Cardiovascular Institute AF Program"}]->(d);
