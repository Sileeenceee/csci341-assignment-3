INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1,  'Arman',   'Armanov',   'arman.armanov@example.com',   'Nazarbayev University',        'Kazakhstan', '+77010000001'),
 (2,  'Amina',   'Aminova',   'amina.aminova@example.com',   'Al-Farabi Kazakh National University', 'Kazakhstan', '+77010000002'),
 (3,  'Dana',    'Sultanova', 'dana.sultanova@example.com',  'Nazarbayev University',        'Kazakhstan', '+77010000003'),
 (4,  'Yerlan',  'Bekov',     'yerlan.bekov@example.com',    'Astana IT University',         'Kazakhstan', '+77010000004'),
 (5,  'Aigerim', 'Nurlanova', 'aigerim.nurlanova@example.com','KBTU',                        'Kazakhstan', '+77010000005'),
 (6,  'Timur',   'Kassymov',  'timur.kassymov@example.com',  'Satbayev University',          'Kazakhstan', '+77010000006'),
 (7,  'Laura',   'Smith',     'laura.smith@example.com',     'University of Edinburgh',      'United Kingdom', '+441310000007'),
 (8,  'Daniel',  'Chen',      'daniel.chen@example.com',     'National University of Singapore', 'Singapore', '+6560000008'),
 (9,  'Sofia',   'Rossi',     'sofia.rossi@example.com',     'Politecnico di Milano',        'Italy',      '+390200000009'),
 (10, 'Marat',   'Ismailov',  'marat.ismailov@example.com',  'Tashkent University of IT',    'Uzbekistan', '+998710000010'),
 (11, 'Elena',   'Petrova',   'elena.petrova@example.com',   'ITMO University',              'Russia',     '+78120000011'),
 (12, 'Nurlan',  'Abenov',    'nurlan.abenov@example.com',   'Nazarbayev University',        'Kazakhstan', '+77010000012'),
 (13, 'Kenji',   'Tanaka',    'kenji.tanaka@example.com',    'University of Tokyo',          'Japan',      '+81300000013');

INSERT INTO author (author_id, orcid) VALUES
 (1, '0000-0001-0000-0001'), (2, '0000-0001-0000-0002'), (5, '0000-0001-0000-0005'),
 (6, NULL), (8, '0000-0001-0000-0008'), (9, '0000-0001-0000-0009'),
 (12, NULL), (13, '0000-0001-0000-0013');

INSERT INTO author_research_area (author_id, area_label) VALUES
 (1, 'Databases'), (1, 'Query Optimization'),
 (2, 'Machine Learning'), (2, 'Recommender Systems'),
 (5, 'Databases'), (5, 'Machine Learning'),
 (6, 'Data Engineering'),
 (8, 'Databases'), (8, 'Stream Processing'),
 (9, 'Computer Vision'), (9, 'Databases'),
 (12, 'Machine Learning'),
 (13, 'Deep Learning');

INSERT INTO reviewer (reviewer_id, years_experience) VALUES
 (1, 4), (3, 8), (4, 5), (5, 3), (7, 10), (8, 2), (10, 0), (11, 6), (13, 4);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 (1, 'Databases'), (1, 'Query Optimization'),
 (3, 'Databases'), (3, 'Distributed Systems'),
 (4, 'Databases'), (4, 'Machine Learning'),
 (5, 'Databases'),
 (7, 'Machine Learning'), (7, 'Deep Learning'),
 (8, 'Databases'),
 (10, 'Data Privacy'),
 (11, 'Natural Language Processing'), (11, 'Machine Learning'),
 (13, 'Deep Learning');

INSERT INTO conference (conference_id, name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Central Asian Conference on Data Systems', 'CADS 2026',
     'Data management, query processing and data systems research.',
     'Astana', 'Kazakhstan', '2026-06-15', '2026-06-18', '2026-02-15', '2026-04-15'),
 (2, 'Steppe Symposium on Artificial Intelligence', 'SSAI 2026',
     'Machine learning, deep learning and applied AI.',
     'Almaty', 'Kazakhstan', '2026-07-20', '2026-07-23', '2026-03-01', '2026-05-01'),
 (3, 'Silk Road Workshop on Language Technology', 'SRLT 2026',
     'Natural language processing for low-resource languages.',
     'Tashkent', 'Uzbekistan', '2026-09-10', '2026-09-11', '2026-05-01', '2026-07-01');

INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Nazarbayev University'), (1, 'Astana IT University'),
 (2, 'Al-Farabi Kazakh National University'),
 (3, 'Tashkent University of IT');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
 (1, 1), (1, 3), (1, 4), (1, 5), (1, 8), (1, 10), (1, 13),
 (2, 1), (2, 3), (2, 4), (2, 7), (2, 11), (2, 13),
 (3, 7), (3, 10), (3, 11);

INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Query Processing',        'Query optimisation and execution.',       'Databases',        3),
 (2, 1, 'Data Management for ML',  'Data systems that support ML workloads.', 'Machine Learning', 4),
 (3, 1, 'Data Privacy',            'Privacy-preserving data management.',     'Data Privacy',     5),
 (4, 2, 'Deep Learning',           'Architectures and training methods.',     'Deep Learning',    7),
 (5, 2, 'Applied Machine Learning','Applications of ML in industry.',         'Machine Learning', 11),
 (6, 3, 'Language Models',         'Language models for Turkic languages.',   'Natural Language Processing', 11);

INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Query Optimization I',    '2026-06-16', '10:00', '12:00', 'Room A1', 3),
 (2, 1, 'Late-Breaking Results',   '2026-06-17', '14:00', '15:30', 'Room B2', 4),
 (3, 2, 'Deep Learning Advances',  '2026-07-21', '09:00', '10:30', 'Hall 1',  7),
 (4, 3, 'Opening Panel',           '2026-09-10', '09:00', '10:00', 'Aula',    11);

INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1, 1, 'Adaptive Join Ordering with Learned Cardinalities',
     'We combine Machine Learning cardinality models with a classic dynamic-programming optimizer.',
     '2026-02-01', 'accepted', 1),
 (2, 1, 'Vectorized Execution for Columnar Stores',
     'A vectorized execution engine for analytical queries on columnar storage.',
     '2026-02-03', 'accepted', 1),
 (3, 2, 'Feature Stores at Scale',
     'Design of a feature store serving machine learning pipelines with low latency.',
     '2026-02-05', 'accepted', NULL),
 (4, 2, 'Lessons from Labelling Pipelines',
     'An experience report on crowd-sourced labelling for training data.',
     '2026-02-06', 'withdrawn', NULL),
 (5, 1, 'Cost Models for Serverless Query Engines',
     'Early results on cost-based optimisation for serverless SQL.',
     '2026-02-07', 'withdrawn', NULL),
 (6, 1, 'Automatic Index Tuning Revisited',
     'Revisiting what-if index tuning on modern workloads.',
     '2026-02-08', 'rejected', NULL),
 (7, 1, 'Low-Latency Stream Joins',
     'Window joins for high-velocity event streams.',
     '2026-02-10', 'submitted', NULL),
 (8, 2, 'Data Cleaning for Tabular Models',
     'Automated detection of label noise and outliers in tabular datasets.',
     '2026-02-11', 'under review', NULL),
 (9, 4, 'Robust Vision Transformers',
     'Robustness of vision transformers to distribution shift.',
     '2026-02-20', 'withdrawn', NULL),
 (10, 4, 'Efficient Training of Convolutional Networks',
     'Mixed-precision and pruning techniques to reduce training cost.',
     '2026-02-22', 'accepted', 3),
 (11, 5, 'Crop Yield Prediction in Kazakhstan',
     'We apply MACHINE LEARNING models to satellite imagery to predict crop yield.',
     '2026-02-24', 'rejected', NULL),
 (12, 5, 'Session-Based Recommendations for E-Commerce',
     'Recurrent models for next-item recommendation.',
     '2026-02-25', 'accepted', NULL),
 (13, 4, 'Sparse Mixture-of-Experts for Small Devices',
     'Compressing mixture-of-experts models for edge deployment.',
     '2026-02-27', 'under review', NULL);

INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 5, 1, TRUE),  (1, 6, 2, FALSE),
 (2, 9, 1, TRUE),  (2, 13, 2, FALSE),
 (3, 6, 1, TRUE),  (3, 5, 2, FALSE), (3, 12, 3, FALSE),
 (4, 2, 1, TRUE),  (4, 9, 2, FALSE),
 (5, 2, 1, TRUE),
 (6, 1, 1, TRUE),  (6, 8, 2, FALSE),
 (7, 8, 1, TRUE),
 (8, 12, 1, TRUE), (8, 2, 2, FALSE),
 (9, 13, 1, TRUE), (9, 2, 2, FALSE),     -- withdrawn, but Amina is NOT corresponding -> kept by 4.1
 (10, 1, 1, TRUE), (10, 9, 2, FALSE),
 (11, 12, 1, TRUE),
 (12, 2, 1, TRUE), (12, 6, 2, FALSE),    -- Amina corresponding, but accepted -> kept by 4.1
 (13, 13, 1, TRUE);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
 (1, 'join ordering'), (1, 'cardinality estimation'), (1, 'machine learning'),
 (2, 'vectorization'), (2, 'column stores'),
 (3, 'feature store'), (3, 'MLOps'),
 (4, 'data labelling'),
 (5, 'serverless'), (5, 'cost models'),
 (6, 'index tuning'),
 (7, 'stream processing'), (7, 'joins'),
 (8, 'data cleaning'),
 (9, 'vision transformers'), (9, 'robustness'),
 (10, 'CNN'), (10, 'pruning'),
 (11, 'agriculture'), (11, 'remote sensing'),
 (12, 'recommender systems'),
 (13, 'mixture of experts'), (13, 'edge AI');

INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, 'papers/1/v1.pdf', '2026-02-01 10:15:00', NULL),
 (1, 2, 'papers/1/v2.pdf', '2026-05-10 18:30:00', 'Camera-ready version'),
 (2, 1, 'papers/2/v1.pdf', '2026-02-03 09:00:00', NULL),
 (3, 1, 'papers/3/v1.pdf', '2026-02-05 11:45:00', NULL),
 (3, 3, 'papers/3/v3.pdf', '2026-05-12 16:20:00', 'Addressed reviewer comments'),
 (4, 1, 'papers/4/v1.pdf', '2026-02-06 13:00:00', NULL),
 (5, 1, 'papers/5/v1.pdf', '2026-02-07 08:10:00', NULL),
 (6, 1, 'papers/6/v1.pdf', '2026-02-08 20:05:00', NULL),
 (7, 1, 'papers/7/v1.pdf', '2026-02-10 12:00:00', NULL),
 (8, 1, 'papers/8/v1.pdf', '2026-02-11 15:30:00', NULL),
 (8, 2, 'papers/8/v2.pdf', '2026-02-14 09:40:00', 'Fixed typos'),
 (9, 1, 'papers/9/v1.pdf', '2026-02-20 10:00:00', NULL),
 (10, 1, 'papers/10/v1.pdf', '2026-02-22 14:00:00', NULL),
 (10, 2, 'papers/10/v2.pdf', '2026-06-01 10:00:00', 'Camera-ready version'),
 (11, 1, 'papers/11/v1.pdf', '2026-02-24 17:25:00', NULL),
 (12, 1, 'papers/12/v1.pdf', '2026-02-25 19:00:00', NULL),
 (13, 1, 'papers/13/v1.pdf', '2026-02-27 07:55:00', NULL);

INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1,  1, 3,  5, 'accept', 'Strong paper with convincing experiments.', NULL,                    '2026-03-20'),
 (2,  1, 4,  4, 'accept', 'Good idea; clarify the training cost.',     NULL,                    '2026-03-22'),
 (3,  1, 13, 4, 'accept', 'Well written.',                              'Solid accept.',         '2026-03-25'),
 (4,  2, 3,  4, 'accept', 'Nice engineering contribution.',             NULL,                    '2026-03-21'),
 (5,  2, 1,  5, 'accept', 'Excellent evaluation.',                      NULL,                    '2026-03-28'),
 (6,  3, 4,  4, 'accept', 'Relevant to practitioners.',                 NULL,                    '2026-03-30'),
 (7,  3, 8,  3, 'accept', 'Borderline; more baselines needed.',         'Weak accept.',          '2026-04-02'),
 (8,  4, 3,  2, 'reject', 'Limited novelty.',                           NULL,                    '2026-03-18'),
 (9,  6, 3,  2, 'reject', 'Results do not generalise.',                 NULL,                    '2026-03-19'),
 (10, 6, 5,  1, 'reject', 'Missing related work.',                      'Clear reject.',         '2026-03-26'),
 (11, 8, 4,  3, 'accept', 'Promising, needs more datasets.',            NULL,                    '2026-04-05'),
 (12, 10, 7, 5, 'accept', 'Impressive speed-ups.',                      NULL,                    '2026-04-10'),
 (13, 10, 4, 4, 'accept', 'Good ablation study.',                       NULL,                    '2026-04-12'),
 (14, 11, 7, 2, 'reject', 'Evaluation on a single region only.',        NULL,                    '2026-04-11'),
 (15, 11, 11,2, 'reject', 'Baselines are weak.',                        NULL,                    '2026-04-15'),
 (16, 12, 11,4, 'accept', 'Clear and useful.',                          NULL,                    '2026-04-16'),
 (17, 12, 13,5, 'accept', 'Very strong empirical results.',             NULL,                    '2026-04-18'),
 (18, 13, 7, 3, 'accept', 'Interesting but preliminary.',               NULL,                    '2026-04-20');

SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),                (SELECT MAX(user_id)       FROM app_user));
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),        (SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track', 'track_id'),                  (SELECT MAX(track_id)      FROM track));
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'),   (SELECT MAX(session_id)    FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),                  (SELECT MAX(paper_id)      FROM paper));
SELECT setval(pg_get_serial_sequence('review', 'review_id'),                (SELECT MAX(review_id)     FROM review));