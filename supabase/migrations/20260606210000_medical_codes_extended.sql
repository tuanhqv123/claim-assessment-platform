-- Extended ICD-10 medical codes for realistic test coverage.
-- Safe to re-run: ON CONFLICT (diagnosis_code) DO NOTHING.

insert into medical_codes (diagnosis_code, description, valid_procedures, procedure_descriptions)
values
  -- Respiratory
  ('J06.9',  'Acute upper respiratory infection, unspecified',
   '["99213","99214","87880","71046"]',
   '{"99213":"Office/outpatient visit, low complexity","99214":"Office/outpatient visit, moderate complexity","87880":"Rapid strep test","71046":"Chest X-ray"}'),

  ('J18.9',  'Pneumonia, unspecified organism',
   '["99214","99215","71046","71048","87590"]',
   '{"99214":"Office visit","99215":"Complex office visit","71046":"Chest X-ray 2 views","71048":"Chest X-ray 4 views","87590":"Bacterial culture"}'),

  -- Hernia (inpatient surgery)
  ('K40.90', 'Inguinal hernia, unilateral, without obstruction or gangrene',
   '["49505","49507","49520"]',
   '{"49505":"Repair initial inguinal hernia age 5+, reducible","49507":"Repair initial inguinal hernia age 5+, incarcerated","49520":"Repair recurrent inguinal hernia, reducible"}'),

  ('K43.9',  'Ventral hernia without obstruction or gangrene',
   '["49560","49565","49568"]',
   '{"49560":"Repair incisional hernia, reducible","49565":"Repair recurrent incisional hernia, reducible","49568":"Implantation of mesh"}'),

  -- Dental
  ('K02.1',  'Dental caries on smooth surface',
   '["D2391","D2392","D2393","D2394"]',
   '{"D2391":"Resin-based composite 1 surface, posterior","D2392":"Resin-based composite 2 surfaces, posterior","D2393":"Resin-based composite 3 surfaces, posterior","D2394":"Resin-based composite 4+ surfaces, posterior"}'),

  ('K04.0',  'Pulpitis',
   '["D3310","D3320","D3330","D3346"]',
   '{"D3310":"Endodontic therapy, anterior tooth","D3320":"Endodontic therapy, premolar","D3330":"Endodontic therapy, molar","D3346":"Retreatment of previous root canal, anterior"}'),

  -- Cardiac
  ('I10',    'Essential (primary) hypertension',
   '["99213","99214","93000","36415"]',
   '{"99213":"Office visit","99214":"Office visit moderate complexity","93000":"ECG with interpretation","36415":"Blood draw"}'),

  -- Orthopaedic
  ('M54.5',  'Low back pain',
   '["99213","99214","72100","72110","97110","97010"]',
   '{"99213":"Office visit","99214":"Office visit moderate complexity","72100":"X-ray lumbar spine 2 views","72110":"X-ray lumbar spine 4+ views","97110":"Therapeutic exercise","97010":"Hot/cold pack application"}'),

  -- Obstetrics
  ('Z34.00', 'Encounter for supervision of normal pregnancy, unspecified trimester',
   '["99213","99214","76801","76805","81025"]',
   '{"99213":"Prenatal visit","99214":"Prenatal visit moderate","76801":"OB ultrasound < 14 weeks","76805":"OB ultrasound 14+ weeks","81025":"Urine pregnancy test"}'),

  -- Diabetes
  ('E11.9',  'Type 2 diabetes mellitus without complications',
   '["99213","99214","82947","83036","36415"]',
   '{"99213":"Office visit","99214":"Office visit moderate","82947":"Glucose quantitative","83036":"Hemoglobin A1c","36415":"Blood draw"}')

on conflict (diagnosis_code) do nothing;
