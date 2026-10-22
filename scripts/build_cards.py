"""Build the first manually curated canonical dataset (not automatic extraction).

Run: python scripts/build_cards.py
Then: python scripts/validate_cards.py --input data/cards/cards.jsonl

The clinical facts below were authored from visually reviewed assigned pages.
This script packages them reproducibly; it does not run an LLM, OCR, retrieval,
clinical evaluation or the future applicability checker.
"""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'Preserve unknown values; identify missing prerequisites; withhold the dependent action until assessed; retain independently supported recommendations.'


def leaf(field, value=True, op='eq', evidence=1):
    return {'op': op, 'field': field, 'value': value, '_evidence': evidence}


def all_of(*conditions):
    return {'op': 'all', 'conditions': list(conditions)}


def any_of(*conditions):
    return {'op': 'any', 'conditions': list(conditions)}


def fact(page, locator, passage, kind='text'):
    return {'pdf_page': page, 'locator': locator, 'passage': passage, 'kind': kind}


def med(name, dose=None, route=None, frequency=None, duration=None, instructions=None, evidence=(1,)):
    return dict(name=name, dose=dose, route=route, frequency=frequency, duration=duration,
                instructions=instructions, _evidence=list(evidence))


def build():
    manifest = json.loads((ROOT / 'sources/source_manifest.json').read_text(encoding='utf-8-sig'))
    sources = {s['source_id']: s for s in manifest['sources']}
    source_for = {'dengue': 'BD_DENGUE_2025_5E', 'hypertension': 'BD_HTN_2023_2E',
                  'cholera': 'WHO_CHOLERA_2024', 'chikungunya': 'BD_CHIK_2017'}
    cards = []

    def add(cid, disease, category, title, context, symptoms, conditions, action, facts,
            medications=(), exclusions=(), limitations=()):
        source = sources[source_for[disease]]
        evidence = []
        for number, item in enumerate(facts, 1):
            evidence.append(dict(item, evidence_id=f'{cid}_E{number}', source_id=source['source_id'],
                                 source_title=source['title'], source_version=source['version'],
                                 transcription_note='Manually selected/abridged source transcription; list fragments may be joined, line breaks and comparison symbols normalized. Not a guaranteed verbatim quotation. Original PDF/PNG and locator retain the authoritative context.'))

        def bind(node):
            node = dict(node)
            if node['op'] in ('all', 'any'):
                node['conditions'] = [bind(child) for child in node['conditions']]
            else:
                index = node.pop('_evidence')
                node['evidence_ids'] = [evidence[index-1]['evidence_id']]
            return node

        def fields(node):
            if node['op'] in ('all', 'any'):
                return set().union(*(fields(child) for child in node['conditions']))
            return {node['field']}

        applicability = bind(conditions)
        blocks = [bind(item) for item in exclusions]
        required = fields(applicability)
        for block in blocks:
            required.update(fields(block))
        meds = []
        for item in medications:
            item = dict(item)
            indices = item.pop('_evidence')
            item['evidence_ids'] = [evidence[i-1]['evidence_id'] for i in indices]
            meds.append(item)
        cards.append(dict(schema_version='1.0', card_id=cid, disease=disease,
                          clinical_category=category, title=title, clinical_context=context,
                          relevant_symptoms=list(symptoms), applicability=applicability,
                          exclusions=blocks, required_patient_fields=sorted(required),
                          recommended_action=action, medications=meds, missing_information_policy=POLICY,
                          evidence=evidence, limitations=list(limitations)))

    # DENGUE: diagnostic explanation, illness-day tests, medicine limit and advice.
    add('DEN_CONSIDER', 'dengue', 'probable_diagnosis', 'Consider dengue in acute febrile illness',
        'Clinical suspicion/differential only; no laboratory confirmation inferred.',
        ['fever', 'headache', 'retro-orbital pain', 'myalgia', 'arthralgia', 'rash'],
        leaf('acute_febrile_illness'),
        'Consider dengue among the differentials. Explain supporting findings; overlapping symptoms may also fit chikungunya or other causes. Do not label a symptom-only case confirmed.',
        [fact(45, 'Section 5.2', 'dengue illness (DF and DHF) should be considered in any patient presenting with an acute febrile illness.'),
         fact(27, 'Section 3.1.2.2', 'high fever, severe headache, retro-orbital pain, myalgia, arthralgia and rashes.'),
         fact(37, 'Differential diagnosis', 'Dengue, chikungunya, and Zika are all mosquito-borne viral diseases that can cause similar symptoms, such as fever, headaches, muscle and joint pain.'),
         fact(45, 'Section 5.1 suspected case', 'Suspected case: Acute febrile illness meeting clinical dengue criteria without confirmatory tests.')],
        limitations=['This card supports consideration, not exclusive diagnosis or complete severity classification.'])
    add('DEN_TEST_EARLY', 'dengue', 'investigations', 'Dengue tests through illness day 5',
        'Suspected dengue at first consultation, with known illness day.', ['fever'],
        all_of(leaf('dengue_suspected'), leaf('illness_day', 1, 'gte'), leaf('illness_day', 5, 'lte')),
        'Suggest CBC/haematocrit and NS1 for diagnostic support and baseline monitoring through day 5; SGOT/SGPT are also listed for early assessment. Do not interpret a negative NS1 alone as exclusion.',
        [fact(45, 'Section 5.2', 'CBC and NS1 Ag up to day 5 and CBC and Dengue Antibody from day 6 onward will support the diagnosis.'),
         fact(41, 'Section 4.1.5', 'Within 5 days: CBC, Haematocrit, Dengue NS1 antigen, SGOT, SGPT'),
         fact(39, 'Section 4.1.1.2', 'This antigen test may become negative from 4-5 days of illness.')])
    add('DEN_TEST_LATE', 'dengue', 'investigations', 'Dengue tests from illness day 6',
        'Suspected dengue with known illness day; serology requires interpretation.', ['fever'],
        all_of(leaf('dengue_suspected'), leaf('illness_day', 6, 'gte')),
        'Suggest CBC and dengue antibody testing from day 6; explain timing. Antibody persistence and paired-sample criteria matter; do not treat a solitary IgG result as proof of current dengue.',
        [fact(45, 'Section 5.2', 'CBC and NS1 Ag up to day 5 and CBC and Dengue Antibody from day 6 onward will support the diagnosis.'),
         fact(39, 'Section 4.1.1.2', 'Level of this IgG may persist at low levels for life long, indicating past dengue infection.')])
    add('DEN_PARACETAMOL_LIMIT', 'dengue', 'medication_guidance', 'Preserve dengue paracetamol daily limit',
        'Fever-control guidance from the home-management section, not a complete prescription.', ['fever'],
        all_of(leaf('dengue_suspected', evidence=2), leaf('fever_present')),
        'For temperature control, retain the source daily ceiling: 3 g/day; in a child, 60 mg/kg/24 hours. Ask age and child weight before individualizing. Do not generate a per-dose schedule, route or duration from this ceiling; clinician review is needed for restrictions and other paracetamol-containing medicines.',
        [fact(47, 'Home management, control of temperature', 'Do not exceed 3 gm/day of paracetamol. (60mg/kg/24hrs in child)'),
         fact(45, 'Section 5.2', 'dengue illness (DF and DHF) should be considered in any patient presenting with an acute febrile illness.'),
         fact(47, 'Control of temperature', 'Warn the patient that the fever may not fully settle with paracetamol and advise not to take excess.')],
        medications=[med('paracetamol', dose='Source daily ceiling: 3 g/day; child 60 mg/kg/24 hours',
                         instructions='Not a per-dose regimen. Fever may not fully settle; do not take excess.', evidence=(1,3))],
        limitations=['No individualized calculation or clinical eligibility assertion; route, dosing frequency and fixed duration not specified in this passage.'])
    add('DEN_HOME_CARE', 'dengue', 'advice', 'Conditional dengue home-care advice',
        'Use only after home-care eligibility assessment; missing risk assessment is not clearance.', ['fever', 'body ache'],
        all_of(leaf('dengue_suspected', evidence=2), leaf('dengue_warning_signs_present', False),
               leaf('coexisting_condition_present', False), leaf('social_risk_present', False),
               leaf('high_risk_condition_present',False,evidence=5),
               leaf('home_management_eligible_assessed',evidence=6)),
        'If clinically suitable for home care, advise rest, mosquito net, tepid sponging, fluids and urine monitoring, and explain warning signs. Numeric fluid planning needs weight and clinical context. Review daily with CBC and follow until afebrile 24-48 hours with stable parameters; return immediately if deterioration occurs.',
        [fact(47, 'Home management', 'Patients without warning signs or coexisting conditions or social risk should get home based care'),
         fact(45, 'Section 5.2', 'dengue illness (DF and DHF) should be considered in any patient presenting with an acute febrile illness.'),
         fact(48, 'Follow up plan of home management', 'Review daily with CBC.'),
         fact(48, 'Follow up plan of home management', 'followed up until the patient become afebrile for 24-48 hours with stable clinical parameters.'),
         fact(46, 'High-risk assessment', 'Patients at high risk for more severe disease and its complications may need admission even without the above criteria. Pregnant women; Elderly; Obesity; Patients on anticoagulants'),
         fact(47, 'Table 7, outpatient row', 'Absent WS; Comorbid condition/High risk for severe disease/Adverse Social condition: Absent; Normal VS & Normal UOP; No immediate risk; Home management as well as followed up and assessed regularly.','table'),
         fact(47, 'Recommended measures in home management', 'Adequate physical rest in comfortable clothing, and preferably under a mosquito net; Tepid sponging for fever; Adequate Hydration; Ensure adequate urine output.')],
        limitations=['Home eligibility must be explicitly assessed by a clinician using examination/CBC/risk context, not inferred solely from absent symptoms. Table 7 threshold overlap and source limitations are recorded in master notes; this card does not automatically clear home care.'])
    add('DEN_AVOID_NSAID', 'dengue', 'medication_guidance', 'Dengue medicine restrictions',
        'Source home-management restrictions; physician-facing medication reconciliation.', ['fever', 'joint pain'],
        leaf('dengue_suspected', evidence=2),
        'Avoid NSAIDs including COX-2 inhibitors and steroids in this dengue context. If taking long-term warfarin, aspirin, clopidogrel or dipyridamole, flag the source withholding advice for clinician/expert review; do not give unconditional self-discontinuation instructions.',
        [fact(48, 'Home management continuation', 'Avoid all NSAIDS (including COX-2 inhibitors) and steroids.'),
         fact(45, 'Section 5.2', 'dengue illness (DF and DHF) should be considered in any patient presenting with an acute febrile illness.'),
         fact(48, 'Home management continuation', 'Temporally withhold warfarin, aspirin, clopidogrel & dipyridamole, in patients who take these on long term basis. Take expert opinion where these drugs are necessary.')])
    add('DEN_URGENT_REVIEW', 'dengue', 'advice', 'Dengue immediate return or hospital review',
        'Return criteria assessed individually; do not require all triggers.', ['abdominal pain', 'bleeding', 'breathing difficulty', 'reduced urine'],
        all_of(leaf('dengue_suspected', evidence=2), any_of(leaf('deterioration_as_fever_settles',evidence=3), leaf('cannot_tolerate_oral_fluids',evidence=3),
               leaf('severe_abdominal_pain',evidence=3), leaf('lethargy_irritability_restlessness',evidence=3), leaf('bleeding_present',evidence=3),
               leaf('reduced_urine_output',evidence=3), leaf('cold_clammy_extremities',evidence=3), leaf('breathing_difficulty',evidence=3))),
        'Advise immediate hospital return/review for any applicable deterioration, oral intolerance, severe pain, mental-status change, bleeding, reduced urine, cold clammy extremities or breathing difficulty. Do not reassure solely because fever settled.',
        [fact(48, 'Indications for immediate return for review / hospitalization', 'Advise patients to return to the hospital immediately, if they develop any of the following conditions:'),
         fact(45, 'Section 5.2', 'dengue illness (DF and DHF) should be considered in any patient presenting with an acute febrile illness.'),
         fact(48, 'Immediate-return list', 'Clinical deterioration with settling of fever; Inability to tolerate oral fluids; Severe abdominal pain; Lethargy or irritability / restlessness; Bleeding tendency like abnormal vaginal bleeding, blood vomiting, black tarry stool, bleeding from nose and gum; Reduced urine output; Cold and clammy extremities; Difficulty in breathing.')],
        limitations=['The final passage joins selected list entries; see original page for bleeding examples and weight/time-dependent urine amounts.'])

    # HYPERTENSION: confirmation exception, investigations, follow-up and restrictions.
    add('HTN_REPEAT_CONFIRM', 'hypertension', 'probable_diagnosis', 'Confirm moderately elevated blood pressure',
        'Moderate initial BP range without the separate >=160/100 or HMOD single-visit exception.', ['elevated blood pressure', 'asymptomatic'],
        all_of(any_of(all_of(leaf('sbp_mmhg',140,'gte'),leaf('sbp_mmhg',159,'lte')),
                      all_of(leaf('dbp_mmhg',90,'gte'),leaf('dbp_mmhg',99,'lte'))),
               leaf('sbp_mmhg',160,'lt'), leaf('dbp_mmhg',100,'lt'), leaf('hmod_present',False)),
        'Treat this as requiring confirmation, not a confirmed diagnosis from one reading. Repeat measurements on three separate occasions within 1-4 weeks; use the same arm. HBPM/ABPM confirmation if possible. The source generally specifies at least three measurements per visit.',
        [fact(46,'Section 4.1','When the initial SBP is between 140 and 159 mmHg, or the DBP is between 90 and 99 mmHg, repeat measurements should be performed on three separate occasions within a period of 1 to 4 weeks'),
         fact(46,'Section 4.1 measurement details','All measurements should be taken in the same arm. If possible and available, the diagnosis of hypertension should be confirmed by out-of-office BP measurement (i.e., HBPM and/or ABPM).'),
         fact(65,'Section 5.3.4 follow-up','A monthly follow up after initiation or a change in antihypertensive medications until patients reach target should be done.'),
         fact(46,'Section 4.1 general confirmation','at least three blood pressure measurements per visit and at least two to three visits at 1-4-week intervals (depending on the BP level)')],
        exclusions=[leaf('previous_bp_confirmation_documented',evidence=3)],
        limitations=['Explicit exclusion of documented prior confirmation scopes this new-diagnosis card to avoid contradicting established-treatment follow-up; this is an operational context choice, not a new BP threshold.'])
    add('HTN_HIGH_BP_ASSESS', 'hypertension', 'probable_diagnosis', 'Higher BP or HMOD confirmation exception',
        'Diagnostic-assessment exception; no unconditional medication initiation from this card.', ['elevated blood pressure'],
        all_of(leaf('hypertension_under_assessment'), any_of(leaf('sbp_mmhg',160,'gte'), leaf('dbp_mmhg',100,'gte'),leaf('hmod_present'))),
        'The guideline may permit diagnosis on a single visit in the appropriate higher-BP/HMOD context. Prompt clinician evaluation rather than universally delaying for routine repeat visits. If hypertension is not established despite HMOD, investigate alternative causes; HMOD alone must not automatically label normal BP as hypertension.',
        [fact(46,'Section 4.1','The diagnosis might be made on a single visit, if BP is >=160/100 mmHg or there is accompanying evidence of hypertension mediated organ damage (HMOD)'),
         fact(48,'Initial evaluation','If hypertension is not diagnosed but there is evidence of HMOD, consider carrying out investigations for alternative causes of HMOD.')],
        limitations=['Comparison signs normalized; pregnancy, age, acute symptoms and clinical assessment still affect management. The internal assessment-context flag is not proof of diagnosis.'])
    add('HTN_INITIAL_TESTS', 'hypertension', 'investigations', 'Hypertension initial investigations with access caveat',
        'Assessment of suspected/established hypertension; tests must not impede indicated treatment.', ['elevated blood pressure'],
        leaf('hypertension_under_assessment'),
        'Assess sodium, potassium, creatinine/eGFR, urine dipstick and ECG; lipids/fasting glucose if available. Evaluate HMOD as indicated. In low-resource settings, testing should not delay otherwise indicated treatment; this does not remove drug-specific monitoring requirements.',
        [fact(51,'Section 4.2.2','treatment should not be delayed, and testing can be done subsequently.'),
         fact(51,'Section 4.2.2, initial tests','Sodium, potassium, serum creatinine and estimated glomerular filtration rate, (eGFR); If available lipid profile and fasting glucose; Urine analysis: Dipstick urine test; 12-lead ECG')],
        limitations=['The assessment-context predicate is an internal clinical routing flag, not a patient-entered disease-name requirement.'])
    # Import the already validated selected representation without changing its identity.
    cards.append(json.loads((ROOT / 'data/cards/examples/HTN_STEP2_FOLLOWUP.json').read_text(encoding='utf-8-sig')))
    add('HTN_PREGNANCY_RESTRICTION', 'hypertension', 'medication_guidance', 'Pregnancy and pregnancy-potential restrictions',
        'Do not conflate current pregnancy referral with the nonpregnant pregnancy-potential branch.', ['elevated blood pressure'],
        all_of(leaf('hypertension_under_assessment'), any_of(leaf('pregnant'), leaf('may_become_pregnant'))),
        'Do not use the standard Figure 8 protocol in current pregnancy; refer to specialist. For patients who may become pregnant, do not prescribe losartan/ACE inhibitor/ARB. The distinct nonpregnant branch uses amlodipine with review; do not substitute that for pregnancy care.',
        [fact(64,'Figure 8, warning and footnote ***','DO NOT PRESCRIBE losartan or any ACE inhibitor or ARB to women who may become pregnant. This protocol should not be used for pregnant patients. If patient is pregnant, refer to a specialist.','figure')])
    add('HTN_FOLLOWUP', 'hypertension', 'advice', 'Follow-up after antihypertensive treatment change',
        'Existing treatment and clinician-assessed target status; not a fixed prescription duration.', ['elevated blood pressure'],
        leaf('on_antihypertensive_treatment'),
        'After initiation or a change, follow monthly until target BP; once target achieved, follow every 3-6 months. Individual target depends on comorbidity/CVD risk; do not assume one target for all patients.',
        [fact(65,'Section 5.3.4','A monthly follow up after initiation or a change in antihypertensive medications until patients reach target should be done. Once target BP is achieved, follow-up at three to six-month interval is appropriate.')])
    add('HTN_LIFESTYLE', 'hypertension', 'advice', 'Source-supported hypertension lifestyle advice',
        'Select patient-relevant advice with comorbidity context; not all source foods fit every patient.', ['elevated blood pressure'],
        leaf('hypertension_under_assessment'),
        'Discuss avoiding alcohol/tobacco/secondhand smoke, exercise 2.5 hours/week, salt under 1 teaspoon/day, heart-healthy diet and weight loss if overweight. Do not add unsupported numeric goals or ignore exercise/renal restrictions.',
        [fact(64,'Figure 8, advice for lifestyle modification','Avoid alcohol and tobacco, including secondhand smoke. Exercise 2.5 hr/week. Eat a low salt diet (under 1 tsp/day). Eat a heart-healthy diet. If overweight, lose weight.','figure')])

    # CHOLERA: outbreak-dependent case definition, hydration assessment and plans.
    add('CHO_CASE_DEFINITION', 'cholera', 'probable_diagnosis', 'Suspected cholera depends on outbreak context',
        'Presentation branch for living patients; death-reporting branch not implemented.', ['acute watery diarrhoea'],
        all_of(leaf('acute_watery_diarrhoea'), any_of(leaf('cholera_outbreak_declared'),
               all_of(leaf('cholera_outbreak_declared',False),leaf('age_years',2,'gte'),leaf('severe_dehydration_present')))),
        'Consider suspected cholera when the source case definition is met. Outbreak status, age and dehydration matter outside an outbreak. This is not microbiological confirmation; if not met, assess other diarrhoeal causes rather than dismissing the patient.',
        [fact(5,'Flowchart case-definition heading','Outside of cholera outbreak: any patient >=2 years presenting with acute watery diarrhoea and severe dehydration or dying from acute watery diarrhoea. Where a cholera outbreak is declared: any person presenting with or dying from acute watery diarrhoea.','figure')])
    danger = any_of(leaf('lethargic_or_unconscious'),leaf('absent_or_weak_pulse'),leaf('respiratory_distress'))
    severe_features = any_of(all_of(leaf('sunken_eyes'),leaf('drinks_poorly_or_unable')),
                             all_of(leaf('sunken_eyes'),leaf('skin_pinch_very_slow')),
                             all_of(leaf('drinks_poorly_or_unable'),leaf('skin_pinch_very_slow')))
    add('CHO_SEVERE_ASSESS', 'cholera', 'investigations', 'Assess severe dehydration and admission',
        'Hydration assessment within suspected-cholera pathway; severe branch has priority.', ['watery diarrhoea', 'poor drinking', 'weak pulse'],
        all_of(leaf('cholera_suspected'),any_of(danger,severe_features)),
        'Assess/manage as severe dehydration with admission and Plan C when at least one listed danger sign OR at least two listed severe dehydration signs are present. Obtain missing assessment details; do not infer severity from sunken eyes alone.',
        [fact(6,'Severe dehydration row','One or more danger signs: Lethargic or unconscious; Absent or weak pulse; Respiratory distress OR at least 2 of the following: Sunken eyes; Not able to drink or drinks poorly; Skin pinch goes back very slowly. Plan C. Admit: Yes.','table')])
    add('CHO_PLAN_B', 'cholera', 'medication_guidance', 'Plan B initial oral rehydration',
        'Clinician-assessed some dehydration, no severe dehydration/danger signs; actual weight required for total.', ['watery diarrhoea', 'thirst'],
        all_of(leaf('cholera_suspected'),leaf('dehydration_class','some',evidence=3),leaf('danger_signs_present',False,evidence=3)),
        'Plan B uses ORS 75 mL/kg over 4 hours; obtain weight before calculating volume. Admit per the assessment table, reassess at least hourly and give additional ORS for ongoing losses. Escalate if severe dehydration or severe vomiting develops.',
        [fact(5,'Plan B box','Give oral rehydration solution (ORS) over 4 hours, 75 mL/kg:','figure'),
         fact(9,'Treatment for some dehydration','Reassess at least every hour; Give additional ORS to replace ongoing losses in addition to fluids in the table'),
         fact(6,'Some dehydration row','No danger signs AND at least 2 of the following: Irritable or restless; Sunken eyes; Rapid pulse; Thirsty (drinks eagerly); Skin pinch goes back slowly. Plan B. Admit: Yes.','table')],
        medications=[med('oral rehydration solution (ORS)',dose='75 mL/kg over 4 hours',route='oral',duration='Initial rehydration over 4 hours',
                         instructions='Actual weight needed for total; additional ongoing-loss replacement and reassessment are separate.',evidence=(1,2))],
        limitations=['Age/weight bands differ between pages 5 and 9; this card uses the explicit page 5 weight-based formula, not merged approximate bands.'])
    add('CHO_PLAN_C', 'cholera', 'medication_guidance', 'Plan C age-dependent IV rehydration',
        'Severe dehydration in clinician-managed facility, with actual age and weight assessment.', ['watery diarrhoea', 'severe dehydration'],
        all_of(leaf('cholera_suspected'),leaf('dehydration_class','severe')),
        'Start IV Ringer lactate immediately. Under 12 months: 30 mL/kg in 1 hour then 70 mL/kg in 5 hours; age 12 months or older: 30 mL/kg in 30 minutes then 70 mL/kg in 2.5 hours. Ask missing age/weight before individualized amounts; reassess every 15-30 minutes and add ORS when drinking safely.',
        [fact(7,'Plan C table','Infants (<12 months): first give 30 mL/kg in 1 hour, then give 70 mL/kg in 5 hours. All others (12 months+): 30 minutes, then 2.5 hours.','table'),
         fact(7,'Plan C instructions','Start intravenous fluid immediately; Ringers lactate is the first choice; Reassess at least every 15 to 30 minutes; Give ORS to replace ongoing losses as soon as the patient can drink safely')],
        medications=[med('Ringer lactate',dose='30 mL/kg followed by 70 mL/kg',route='intravenous',
                         duration='6 hours for <12 months; 3 hours for >=12 months',
                         instructions='Age-dependent initial/subsequent phase timings and repeated clinical reassessment are required.',evidence=(1,2))],
        limitations=['Formula and age bands retained as text; automated dose calculation is not implemented. Do not use one adult rate for infants.'])
    add('CHO_ANTIBIOTIC_ELIGIBILITY', 'cholera', 'medication_guidance', 'Conditional cholera antibiotic options',
        'Eligibility includes severe dehydration OR pregnancy OR elderly status, not all cholera cases.', ['watery diarrhoea'],
        all_of(leaf('cholera_suspected'),any_of(leaf('dehydration_class','severe'),leaf('pregnant'),leaf('elderly_assessed'))),
        'For eligible patients, show source single-dose options for clinician selection: doxycycline preferred, azithromycin alternative. Ask age, weight where needed, allergies and clinical restrictions before individualizing; do not automatically give both medicines.',
        [fact(5,'Antibiotic footnote','Antibiotics for all patients with severe dehydration, pregnant women and the elderly: Preferred is doxycycline single dose (200 mg for under 12 years, or 300 mg for older children and adults. Alternative is azithromycin single dose (20 mg/kg for under 12 years, or 1 g for older children and adults.','footnote'),
         fact(11,'Antibiotics note','All pregnant women and elderly patients should receive antibiotics regardless of their hydration status or treatment plan')],
        medications=[med('doxycycline',dose='<12 years: 200 mg; older children/adults: 300 mg',frequency='single dose',duration='single dose',
                         instructions='Preferred option in this source; clinician selection and contraindication review required.'),
                     med('azithromycin',dose='<12 years: 20 mg/kg; older children/adults: 1 g',frequency='single dose',duration='single dose',
                         instructions='Alternative, not an automatic additional antibiotic.')],
        limitations=['Route and numerical elderly threshold are not specified here. Pediatric doxycycline dose is literal source text, not a derived mg/kg amount.'])
    add('CHO_DISCHARGE', 'cholera', 'advice', 'Cholera discharge readiness and supplies',
        'All listed flowchart discharge conditions must be assessed, with age/function caveats.', ['diarrhoea'],
        all_of(leaf('cholera_suspected'),leaf('dehydration_class','none'),leaf('ors_without_vomiting'),
               leaf('hours_without_watery_stool',4,'gte'),leaf('walks_without_assistance'),leaf('passing_urine')),
        'Consider discharge after all listed recovery conditions, with clinician judgement. Supply at least 4 ORS packets; explain seeking treatment for at least 3 diarrhoea episodes in 24 hours and prevention. For a paediatric patient, supply zinc to complete 10 days if applicable.',
        [fact(5,'Discharge box','Has no signs of dehydration AND Takes ORS without vomiting AND Has no watery stools for 4 hours AND Is able to walk without assistance AND Is passing urine','figure'),
         fact(14,'Discharge assessment','Provide at least 4 packets of ORS for all patients who are discharged to use at home.'),
         fact(14,'Discharge assessment','anyone with at least 3 episodes of diarrhoea in 24 hours should seek treatment.'),
         fact(14,'Discharge assessment','For paediatric patients give sufficient zinc to complete 10 days treatment.'),
         fact(14,'Prevention education','Ensure all patients and their caregivers understand how to prevent cholera before discharge.')],
        limitations=['Walking criterion is literal source wording and may not apply to infants/nonambulatory patients; do not invent an alternative clearance rule. No zinc dose individualized here.'])

    # CHIKUNGUNYA: differential, tests, conditional symptom care and recovery.
    add('CHIK_CONSIDER', 'chikungunya', 'probable_diagnosis', 'Consider chikungunya with fever and severe joint symptoms',
        'Clinical criteria alone support possible disease; epidemiology/labs affect certainty.', ['fever', 'severe arthralgia', 'arthritis', 'rash'],
        all_of(leaf('acute_fever_onset'),leaf('temperature_c',38.5,'gt'),leaf('severe_arthralgia_or_arthritis'),
               leaf('joint_symptoms_explained_by_other_condition',False)),
        'Consider possible chikungunya. Ask residence/travel/transmission history for epidemiological criteria before calling it formally probable; use timed laboratory criteria for confirmation. Retain dengue as a differential/co-infection possibility.',
        [fact(11,'Clinical criteria and case definition','acute onset of fever >38.5 degrees C; severe arthralgia/arthritis not explained by other medical conditions. Possible case: a patient meeting only clinical criteria'),
         fact(11,'Epidemiological criteria','Residing or having visited epidemic areas; having reported transmission within 15 days prior to the onset of symptoms'),
         fact(18,'Chikungunya and dengue','The viruses can circulate in the same area and cause occasional co-infections in the same patient')])
    add('CHIK_TEST_TIMING', 'chikungunya', 'investigations', 'Chikungunya investigations depend on illness timing',
        'Clinical suspicion with day of illness required before selecting timed specific tests.', ['fever', 'joint pain'],
        leaf('chikungunya_suspected'),
        'Consider CBC/inflammatory markers and SGPT as appropriate. Ask illness day: RT-PCR within first 5 days; specific IgM sample days 5-28; paired IgG fourfold rise requires samples at least 3 weeks apart, first after day 7. Preserve the source caution about poor ICT kit validity. CSF only when neurological features indicate.',
        [fact(22,'Specific laboratory investigations','Presence of viral RNA by real Time RT-PCR (Within 5 days of onset of Illness); Presence of viral specific IgM antibody in single serum sample collected within 5 to 28 days of onset Fever; Four-fold Rise of IgG antibody in samples collected at least three weeks apart (1st sample after 7 days)'),
         fact(22,'N.B. 1','Diagnostic validity of currently available ICT kit for the detection of IgM and IgG for Chikungunya virus is very poor.'),
         fact(21,'Laboratory diagnosis','Blood or Serum; CSF (if neurological features present); CBC; ESR: Usually Elevated; C-Reactive Protein: Increased during the Acute Phase'),
         fact(22,'Routine investigations continuation','SGPT: Elevated')],
        limitations=['ICT statement is from 2017; no current kit/service availability claim or routine universal advanced-testing panel.'])
    add('CHIK_DENGUE_PRECAUTION', 'chikungunya', 'medication_guidance', 'Keep dengue precautions until exclusion',
        'Suspected chikungunya may overlap with dengue; exclusion must be assessed, not inferred from one symptom.', ['fever', 'joint pain', 'rash'],
        leaf('chikungunya_suspected'),
        'Until dengue is ruled out, retain dengue-oriented precautions. Avoid self-medication with aspirin/NSAIDs; do not take a chikungunya label as permission for NSAIDs. First 10 days and adequate dengue exclusion remain relevant to later clinician decisions.',
        [fact(18,'Chikungunya and dengue','Patients with suspected chikungunya should be managed as dengue until dengue has been ruled out'),
         fact(20,'Hospital management continuation','Aspirin or NSAIDs should be avoided during first 10 days. NSAIDs can be used in Chikungunya only when Dengue fever is adequately excluded.'),
         fact(19,'Home management continuation','Avoid self medication with aspirin or NSAIDs.')])
    add('CHIK_PARACETAMOL_SOURCE', 'chikungunya', 'medication_guidance', 'Chikungunya paracetamol conditions and source limits',
        'Symptomatic fever care only after clinician assessment, with dengue excluded and liver/kidney restriction checked.', ['fever', 'joint pain'],
        all_of(leaf('chikungunya_suspected'),leaf('fever_present'),leaf('dengue_excluded_by_clinician',evidence=2),
               leaf('preexisting_liver_or_kidney_disease',False)),
        'Show the chikungunya-source paracetamol guidance for clinician review, preserving liver/kidney restriction and age/weight needs. Adult source allows up to 1000 mg four times daily; child source is 50-60 mg/kg/day divided doses. Do not use this higher adult maximum when dengue remains possible; fixed duration not supplied.',
        [fact(18,'Home management','Take paracetamol tablets during periods of fever (up to 1000 mg tablets four times daily), in persons with no preexisting liver or kidney disease. Children may be given 50-60 mg per kg body weight per day in divided doses.'),
         fact(18,'Dengue precaution','Patients with suspected chikungunya should be managed as dengue until dengue has been ruled out')],
        medications=[med('paracetamol',dose='Adult: up to 1000 mg; child: 50-60 mg/kg/day in divided doses',
                         frequency='Adult source: four times daily; child division frequency not specified',
                         instructions='Source describes tablets during fever; no pre-existing liver/kidney disease. Verify age and weight; child amount is per day, not per dose.')],
        limitations=['Dengue has a different adult daily limit. No automatic individualized prescription; route not explicitly supplied in this passage.'])
    add('CHIK_ADMISSION', 'chikungunya', 'advice', 'Chikungunya admission criteria',
        'Admission criteria override a generic mild/moderate home-care statement.', ['joint pain', 'bleeding', 'syncope', 'reduced urine'],
        all_of(leaf('chikungunya_suspected'), any_of(leaf('haemodynamic_instability'),leaf('oliguria_assessed_by_clinician',evidence=2),leaf('altered_sensorium'),
               leaf('bleeding_present'),leaf('persistent_disabling_joint_symptoms_after_3_days_treatment'),
               leaf('age_years',60,'gt'),leaf('age_years',1,'lt'),leaf('pregnant'),leaf('chikungunya_high_risk',evidence=3))),
        'Arrange hospital assessment/admission for applicable instability, altered sensorium, bleeding, nonresponse/disabling joint symptoms after three days treatment, age over 60, infancy, pregnancy or high risk. Also assess oliguria; the source lists urine below 500 mL/24 hours, with age/context limitations.',
        [fact(19,'Admission criteria','hemo-dynamically unstable; altered sensorium; bleeding manifestations; persons not responding or having persistent joint pain or disabling arthritis even after three days of symptomatic treatment; persons above sixty years; infants (below one year of age); Pregnancy; High risk Group'),
         fact(19,'Admission criterion 2','oliguria (urine output less than 500 ml in 24 hours)'),
         fact(15,'High risk group','Hypertension, Diabetic, CAD/CVD, Geriatric age, Pregnancy, COPD; Co-infection: Dengue, Tuberculosis, Enteric fever, Pneumonia, HIV, Malaria')],
        limitations=['Oliguria is a clinician-assessed trigger; the numerical source description must not be blindly generalized to infants. High-risk assessment must include source page 15 comorbidity/co-infection context, not a default false value.'])
    add('CHIK_PHASE_ADVICE', 'chikungunya', 'advice', 'Chikungunya phase-dependent movement and follow-up',
        'Distinguish acute rest/normal movement from post-acute rehabilitation.', ['joint pain', 'arthritis', 'stiffness'],
        leaf('chikungunya_suspected'),
        'Ask phase if unknown. Acute phase: cold compresses, rest/avoid exertion, maintain normal movement; no acute physiotherapy indication in the appended opinion. Post-acute: mild exercise and joint positioning; persistent disability/pain may need arthralgia clinic and physical-medicine assessment.',
        [fact(26,'Expert committee opinion, points 3-4','there is no indication of physiotherapy in acute phase. Only cold compression can be advised. Maintain normal movement of joints and body. Mild forms of exercise are recommended in post-acute phase'),
         fact(26,'Expert committee opinion, point 4b','Patients who are suffering for joint pains (arthralgia and arthritis) after acute phase, can be advised to go to arthralgia clinics in hospitals in chronic phase'),
         fact(27,'Expert opinion continuation','benefit of physical medicine depends on lesion assessment and overall impact of the disease (pain, autonomy, quality of life).'),
         fact(18,'Home management rest and activity','Adequate rest in a warm environment; Refrain from exertion.')],
        limitations=['Conditional advice remains in text; phase-specific execution is not yet split into separate rules.'])

    # Development coverage additions: retain the same sources and review provenance.
    add('DEN_WARNING_EDUCATION', 'dengue', 'advice', 'Explain warning signs before deterioration occurs',
        'Anticipatory advice for suspected dengue, including patients currently without warning signs.',
        ['fever', 'abdominal pain', 'vomiting', 'bleeding'], leaf('dengue_suspected'),
        'Explain warning signs and immediate-return triggers even if none is currently present: severe abdominal pain, persistent vomiting, bleeding, altered mental status, fluid accumulation or worsening findings; return immediately for deterioration as fever settles, fluid intolerance, reduced urine, cold clammy limbs or breathing difficulty. Do not treat settling fever as recovery.',
        [fact(47,'Home management final bullet','Patient should be informed about warning sign. (page 28)'),
         fact(28,'Warning signs','Intense continuous abdominal pain or pain when palpating abdomen; Persistent vomiting (>=3 episodes in 1 hr or >=4 in 6 hrs); Fluid accumulation; Mucosal bleeding; Altered mental status; Hepatomegaly (>=2cm below costal margin); Progressive increase of the haematocrit (in at least 2 consecutive measurements taken 6 hours apart)'),
         fact(48,'Immediate return indications','Clinical deterioration with settling of fever; Inability to tolerate oral fluids; Severe abdominal pain; Lethargy or irritability / restlessness; Reduced urine output; Cold and clammy extremities; Difficulty in breathing.')],
        limitations=['Selected warning/return list entries joined; serial Hct definition requires >=2 consecutive measurements 6 hours apart. This educational card does not clear home-care eligibility.'])
    add('HTN_ESTABLISHED_REVIEW', 'hypertension', 'probable_diagnosis', 'Interpret documented hypertension treatment follow-up',
        'Known prior BP confirmation is supplied as patient history; no new diagnosis inferred from one reading.',
        ['persistently elevated blood pressure', 'asymptomatic'],
        all_of(leaf('previous_bp_confirmation_documented'), leaf('on_antihypertensive_treatment',evidence=2)),
        'Explain this as follow-up of documented previously confirmed hypertension. Review current BP against the recorded individual target and treatment history; do not reset every follow-up patient to unconfirmed first-visit status or infer a new diagnosis solely from symptoms.',
        [fact(46,'Section 4.1','The diagnosis of hypertension should be based on multiple blood pressure measurements, taken on separate occasions over a period.'),
         fact(65,'Section 5.3.4','A monthly follow up after initiation or a change in antihypertensive medications until patients reach target should be done.')],
        limitations=['Follow-up explanation is a representation of documented patient history plus source confirmation/follow-up policy; it does not independently verify the historical diagnosis.'])
    some_signs = ['irritable_or_restless', 'sunken_eyes', 'rapid_pulse', 'thirsty_drinks_eagerly', 'skin_pinch_slow']
    two_some_signs = any_of(*(all_of(leaf(a),leaf(b)) for index,a in enumerate(some_signs) for b in some_signs[index+1:]))
    add('CHO_SOME_ASSESS', 'cholera', 'investigations', 'Assess some dehydration after severe branch',
        'Evaluate severe dehydration first; no-danger and severe-branch exclusion must be assessed, not defaulted.',
        ['watery diarrhoea', 'thirst', 'restlessness', 'sunken eyes'],
        all_of(leaf('cholera_suspected'),leaf('danger_signs_present',False),leaf('severe_dehydration_present',False),two_some_signs),
        'Classify as some dehydration when severe criteria are not met, no danger signs are present and at least two listed some-dehydration signs are documented. Recommend admission and Plan B, with reassessment at least hourly; do not select severity from one shared sign.',
        [fact(6,'Some dehydration row','No danger signs AND at least 2 of the following: Irritable or restless; Sunken eyes; Rapid pulse; Thirsty (drinks eagerly); Skin pinch goes back slowly. Plan B. Admit: Yes.','table'),
         fact(5,'Flowchart assessment order and Plan B reassessment','Assess for shock / severe dehydration; Assess for some dehydration; Reassess at least every hour','figure')],
        limitations=['At-least-two represented as OR over ten distinct pairs. Severe-branch precedence is explicit; internal dehydration assessment still needs runtime implementation.'])
    add('CHO_PLAN_B_REASSESS', 'cholera', 'advice', 'Plan B reassessment and separate ongoing-loss replacement',
        'Some-dehydration treatment; age-based per-stool maintenance is distinct from initial 4-hour ORS.',
        ['watery diarrhoea', 'thirst'], all_of(leaf('cholera_suspected'),leaf('dehydration_class','some')),
        'Reassess at least hourly. Give additional ORS for ongoing losses: after each loose stool, <24 months 50-100 mL, age 2-9 years 100-200 mL, age >=10 years as much as wanted. Do not count these as a second copy of the initial rehydration volume. Severe dehydration or severe vomiting requires Plan C review; do not discharge until all source conditions are met.',
        [fact(9,'Plan B instructions','Reassess at least every hour; Give additional ORS to replace ongoing losses in addition to fluids in the table'),
         fact(10,'Maintain hydration Plan B','ORS after each loose stool: <24 months 50-100 mL; 2-9 years 100-200 mL; 10 years+ As much as wanted','table'),
         fact(5,'Plan B reassessment arrows','Severe dehydration OR Severe vomiting','figure')],
        limitations=['Ask age if unknown before choosing a maintenance row; clinical reassessment determines transition, not this text alone.'])
    add('CHIK_PROBABLE_EPIDEMIOLOGY', 'chikungunya', 'probable_diagnosis', 'Chikungunya clinical plus epidemiological criteria',
        'Formal probable classification requires the source clinical AND epidemiological criteria; no laboratory confirmation assumed.',
        ['acute fever', 'severe arthralgia', 'arthritis', 'rash'],
        all_of(leaf('acute_fever_onset'),leaf('temperature_c',38.5,'gt'),leaf('severe_arthralgia_or_arthritis'),
               leaf('joint_symptoms_explained_by_other_condition',False),leaf('residence_or_travel_to_epidemic_area'),
               leaf('reported_transmission_within_15_days_before_onset')),
        'Explain that clinical and epidemiological findings support the source probable-chikungunya category. State which findings match; laboratory confirmation is absent unless source-timed test criteria are met. Continue considering dengue/co-infection; this category does not establish dengue exclusion.',
        [fact(11,'Case definition and criteria','Probable case: a patient meeting both the clinical and epidemiological criteria; acute onset of fever >38.5 degrees C; severe arthralgia/arthritis not explained by other medical conditions; Residing or having visited epidemic areas; having reported transmission within 15 days prior to the onset of symptoms'),
         fact(18,'Chikungunya and dengue','The viruses can circulate in the same area and cause occasional co-infections in the same patient')])
    add('HTN_PREGNANCY_POTENTIAL_ALTERNATIVE', 'hypertension', 'medication_guidance', 'Nonpregnant pregnancy-potential follow-up alternative',
        'Separate Figure 8 pathway, after one month of amlodipine 5 mg daily; current pregnancy is excluded.',
        ['elevated blood pressure'],
        all_of(leaf('age_years',18,'gte',evidence=4),leaf('pregnant',False,evidence=3),leaf('may_become_pregnant'),
               leaf('current_htn_step','amlodipine_5mg_once_daily'),leaf('months_since_step1_started',1,'gte'),
               leaf('bp_target_met',False),leaf('medicines_taken_regularly_correctly',evidence=3)),
        'For clinician consideration, the distinct nonpregnant pregnancy-potential branch increases amlodipine to 10 mg once daily after a month if target is not met and adherence is checked. Review after another month; if still not at target, refer to specialist. Do not use losartan, another ARB or ACE inhibitor. If currently pregnant, refer rather than applying this branch.',
        [fact(64,'Figure 8, women who may become pregnant panel, population heading and footnotes c/***','For Women of Childbearing Age Who May Become Pregnant: Step 1: Start amlodipine 5 mg once daily. Step 2: Review after 1 month. If treatment target not met, amlodipine 10 mg once daily. Step 3: Review after 1 month. If treatment target not met, refer to specialist.','figure'),
         fact(64,'Figure 8 warning','DO NOT PRESCRIBE losartan or any ACE inhibitor or ARB to women who may become pregnant.','figure'),
         fact(64,'Figure 8 footnotes c and ***','Check that the patient has been taking drugs regularly and correctly. This protocol should not be used for pregnant patients. If patient is pregnant, refer to a specialist.','footnote'),
         fact(64,'Figure 8 population','Measure blood pressure of all adults >=18 years','figure')],
        medications=[med('amlodipine',dose='10 mg',frequency='once daily',
                         instructions='Only this assessed follow-up branch; review after one month. Route/fixed duration not specified.')],
        exclusions=[leaf('pregnant',evidence=3)],
        limitations=['Not an initial-dose or pregnancy treatment card; source conditions are not an exhaustive drug-suitability assessment. Adult age and adherence conditions link to population/footnotes within this figure.'])

    investigation_details = {
        'DEN_TEST_EARLY': ('Support dengue diagnosis and baseline blood-count/haematocrit assessment.',
                           'Illness days 1–5.', 'Suspected dengue; negative early NS1 alone does not exclude dengue.'),
        'DEN_TEST_LATE': ('Support dengue diagnosis using CBC and antibody testing; distinguish persistent past IgG from current infection.',
                          'From illness day 6 onward.', 'Interpret antibodies with illness timing and source criteria; isolated IgG is not confirmation.'),
        'HTN_INITIAL_TESTS': ('Assess renal function, electrolytes and organ involvement; consider cardiovascular/metabolic risk tests where available.',
                             'During hypertension assessment; low-resource testing may be done subsequently without delaying indicated treatment.',
                             'Lipids/glucose if available. Drug-specific laboratory monitoring remains necessary.'),
        'CHO_SEVERE_ASSESS': ('Identify danger signs or severe dehydration to guide admission and Plan C assessment.',
                             'Assess severe dehydration first.', 'At least one source-listed danger sign OR two severe-dehydration signs; one shared sign alone is insufficient.'),
        'CHO_SOME_ASSESS': ('Differentiate some dehydration from the severe branch to guide admission and Plan B.',
                           'After severe-branch assessment; reassess at least hourly.',
                           'No danger signs, severe criteria not met, and at least two listed some-dehydration signs.'),
        'CHIK_TEST_TIMING': ('Support chikungunya diagnosis with timing-appropriate virology/serology and relevant blood tests.',
                            'RT-PCR within first 5 days; IgM days 5–28; paired IgG samples at least 3 weeks apart, first after day 7.',
                            'Establish illness day. CSF only with neurological features. Preserve the poor ICT-validity caution.'),
    }
    for card in cards:
        if card['card_id'] in investigation_details:
            purpose, timing, conditions = investigation_details[card['card_id']]
            card['investigation_details'] = {'purpose': purpose, 'timing': timing, 'conditions': conditions,
                                             'evidence_ids': [e['evidence_id'] for e in card['evidence']]}
        if card['card_id'] == 'HTN_STEP2_FOLLOWUP':
            card['monitoring_details'] = {
                'action': 'Check serum creatinine and potassium before initiating losartan and repeat several weeks after starting.',
                'purpose': 'Laboratory monitoring required by the losartan treatment pathway.',
                'timing': 'Before initiation and several weeks after starting losartan.',
                'conditions': 'Only when this losartan-containing treatment branch applies; checked results still require clinician review.',
                'evidence_ids': ['H64_MONITORING']}
    if len({c['card_id'] for c in cards}) != len(cards):
        raise ValueError('Duplicate card IDs')
    out = ROOT / 'data/cards'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'cards.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False)+'\n' for c in cards), encoding='utf-8')
    coverage = Counter((c['disease'], c['clinical_category']) for c in cards)
    report = {
        'card_count': len(cards), 'authoring_method': 'Manually curated evidence, deterministically packaged; no automatic clinical extraction or model call.',
        'coverage': {d: {k: coverage[d,k] for k in ('probable_diagnosis','investigations','medication_guidance','advice')}
                     for d in source_for},
        'status': 'Q1 source/coverage audit revisions prepared; rebuild and structural validation required before marking revised package complete.',
        'limitations': ['Coverage counts do not establish clinical completeness or six-case coverage.',
                        'Applicability execution, normalized patient field contract and final case design pending.']}
    (out / 'build_report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
