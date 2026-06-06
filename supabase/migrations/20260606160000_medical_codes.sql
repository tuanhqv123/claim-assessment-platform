-- ICD-10 diagnosis -> valid procedures reference, moved from
-- data/mappings/icd10_procedures.json into the database (no file/hardcoded data).
create table if not exists medical_codes (
  diagnosis_code         text primary key,
  description            text,
  valid_procedures       jsonb not null default '[]',
  procedure_descriptions jsonb not null default '{}'
);

insert into medical_codes (diagnosis_code, description, valid_procedures, procedure_descriptions) values
  ('J06.9', 'Acute upper respiratory infection, unspecified', '["99213", "99214", "87880", "71046"]'::jsonb, '{"99213": "Office/outpatient visit, established patient, low complexity", "99214": "Office/outpatient visit, established patient, moderate complexity", "87880": "Rapid strep test", "71046": "Chest X-ray, 2 views"}'::jsonb),
  ('K35.80', 'Acute appendicitis, unspecified', '["44950", "44960", "44970"]'::jsonb, '{"44950": "Appendectomy", "44960": "Appendectomy with drainage of abscess", "44970": "Laparoscopic appendectomy"}'::jsonb),
  ('M95.0', 'Acquired deformity of nose', '["30400", "30410", "30420"]'::jsonb, '{"30400": "Rhinoplasty, primary", "30410": "Rhinoplasty, secondary", "30420": "Rhinoplasty with major septal repair"}'::jsonb),
  ('J18.9', 'Pneumonia, unspecified organism', '["99223", "94640", "71046", "87081"]'::jsonb, '{"99223": "Initial hospital care, high complexity", "94640": "Nebulizer treatment", "71046": "Chest X-ray, 2 views", "87081": "Culture, presumptive pathogen"}'::jsonb),
  ('K21.0', 'Gastro-esophageal reflux disease with esophagitis', '["99213", "43239", "91035"]'::jsonb, '{"99213": "Office visit, established patient", "43239": "Upper GI endoscopy with biopsy", "91035": "Esophageal motility study"}'::jsonb),
  ('E11.9', 'Type 2 diabetes mellitus without complications', '["99213", "99214", "83036", "80053"]'::jsonb, '{"99213": "Office visit, established patient", "99214": "Office visit, moderate complexity", "83036": "Hemoglobin A1c test", "80053": "Comprehensive metabolic panel"}'::jsonb),
  ('I10', 'Essential hypertension', '["99213", "99214", "93000", "80053"]'::jsonb, '{"99213": "Office visit, established patient", "99214": "Office visit, moderate complexity", "93000": "Electrocardiogram (ECG)", "80053": "Comprehensive metabolic panel"}'::jsonb),
  ('S52.509A', 'Unspecified fracture of lower end of radius', '["25600", "73110", "29075"]'::jsonb, '{"25600": "Closed treatment of distal radial fracture", "73110": "X-ray of wrist, 3 views", "29075": "Application of forearm cast"}'::jsonb),
  ('K80.20', 'Calculus of gallbladder without cholecystitis', '["47562", "47563", "76700"]'::jsonb, '{"47562": "Laparoscopic cholecystectomy", "47563": "Laparoscopic cholecystectomy with cholangiography", "76700": "Abdominal ultrasound"}'::jsonb),
  ('N39.0', 'Urinary tract infection, site not specified', '["99213", "81001", "87086"]'::jsonb, '{"99213": "Office visit, established patient", "81001": "Urinalysis, automated with microscopy", "87086": "Urine culture"}'::jsonb)
on conflict (diagnosis_code) do update set
  description = excluded.description,
  valid_procedures = excluded.valid_procedures,
  procedure_descriptions = excluded.procedure_descriptions;
