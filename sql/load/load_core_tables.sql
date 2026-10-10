SET NOCOUNT ON;

BEGIN TRY

	BEGIN TRANSACTION;

	/* ============================ */
	/* Identify latest staging load */
	/* ============================ */

	DECLARE @load_run_id UNIQUEIDENTIFIER;

	SELECT TOP 1 
		@load_run_id = load_run_id 
	FROM 
		staging.job_posting_metadata
	ORDER BY loaded_at DESC;


	PRINT(CHAR(13))
	RAISERROR ('=========================================', 0, 1) WITH NOWAIT;
	RAISERROR ('Synchronize core with latest staging load', 0, 1) WITH NOWAIT;
	RAISERROR ('=========================================', 0, 1) WITH NOWAIT;


	/* ============================== */
	/* Identify orphaned job postings */
	/* ============================== */

	-- Temporary table to store IDs of orphaned job postings
	DROP TABLE IF EXISTS #orphaned_job_postings;
	
	CREATE TABLE #orphaned_job_postings (
		job_posting_id INT PRIMARY KEY
	);
	
	-- Identify orphaned job postings in core
	WITH core_job_postings_joined AS 
	(
		SELECT 
			job_posting_id,
			job_id,
			company,
			job_title,
			city,
			region,
			country,
			source_platform,
			original_URL,
			date_collected
		FROM core.job_postings AS j 
		JOIN core.companies AS c
			ON j.company_id = c.company_id
		JOIN core.locations AS l
			ON j.location_id = l.location_id
	),
	orphaned_job_postings AS 
	(
		SELECT * 
		FROM core_job_postings_joined AS c 
		WHERE NOT EXISTS (
			SELECT 1 
			FROM staging.job_posting_metadata AS s
			WHERE s.job_id = c.job_id
				AND s.company = c.company
				AND s.job_title = c.job_title
				AND s.city = c.city
				AND ISNULL(s.region, '') = ISNULL(c.region, '') 
				AND s.country = c.country
				AND s.source_platform = c.source_platform
				AND s.original_url = c.original_URL
				AND s.date_collected = c.date_collected
				AND s.load_run_id = @load_run_id	-- Latest staging load
		)
	)
	INSERT INTO #orphaned_job_postings (job_posting_id)
	SELECT job_posting_id
	FROM orphaned_job_postings;


	/* ================================== */
	/* Identify stale standardized skills */
	/* ================================== */

	-- Temporary table to store IDs of stale standardized skills
	DROP TABLE IF EXISTS #stale_standardized_skills;
	
	CREATE TABLE #stale_standardized_skills (
		standardized_skill_id INT PRIMARY KEY
	);

	
	-- Identify stale standardized skills in core
	WITH core_standardized_skills_joined AS 
	(
		SELECT 
			standardized_skill_id,
			standardized_skill,
			skill_type,
			skill_category,
			skill_subcategory
		FROM core.standardized_skills AS s 
		JOIN core.skill_classifications AS c
			ON s.skill_classification_id = c.skill_classification_id
	),
	stale_standardized_skills AS 
	(
		SELECT * 
		FROM core_standardized_skills_joined AS c 
		WHERE NOT EXISTS (
			SELECT 1 
			FROM staging.skill_taxonomy AS s
			WHERE 
				s.standardized_skill = c.standardized_skill
				AND s.skill_type = c.skill_type
				AND ISNULL(s.skill_category, '') = ISNULL(c.skill_category, '')
				AND ISNULL(s.skill_subcategory, '') = ISNULL(c.skill_subcategory, '')
				AND s.load_run_id = @load_run_id	-- Latest staging load
		)
	)
	INSERT INTO #stale_standardized_skills (standardized_skill_id)
	SELECT standardized_skill_id
	FROM stale_standardized_skills;

	/* ==================================== */
	/* Identify invalid standardized skills */
	/* ==================================== */

	-- Temporary table to store IDs of invalid standardized skills
	DROP TABLE IF EXISTS #invalid_standardized_skills;
	
	CREATE TABLE #invalid_standardized_skills (
		standardized_skill_id INT PRIMARY KEY
	);

	
	-- Identify invalid standardized skills in core
	WITH invalid_standardized_skills AS 
	(
		SELECT 
			standardized_skill_id
		FROM core.standardized_skills AS c 
		JOIN staging.skill_taxonomy AS s
			ON c.standardized_skill = s.standardized_skill
		WHERE 
			(
				s.valid_standardized_skill = 0 
				OR s.valid_classification = 0
			)
			AND s.load_run_id = @load_run_id	-- Latest staging load
	)
	INSERT INTO #invalid_standardized_skills (standardized_skill_id)
	SELECT standardized_skill_id
	FROM invalid_standardized_skills;


	/* ========================== */
	/* SYNCHRONIZE SKILL MENTIONS */
	/* ========================== */

	PRINT CHAR(10) + 'Synchronizing skill mentions...';
	

	-- Delete skill mentions belonging to orphaned job postings --
	DELETE s 
	FROM core.skill_mentions AS s
	JOIN #orphaned_job_postings AS o
		ON s.job_posting_id = o.job_posting_id;

	PRINT '• Orphaned job postings:        ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';
	

	-- Delete stale skill mentions --
	DELETE m
	FROM core.skill_mentions AS m
	JOIN core.job_postings AS j
		ON m.job_posting_id = j.job_posting_id
	JOIN core.standardized_skills AS ss
		ON m.standardized_skill_id = ss.standardized_skill_id
	WHERE NOT EXISTS (
		SELECT 1
		FROM staging.standardized_raw_skills AS s
		WHERE 
			s.job_id = j.job_id
			AND s.extracted_skill = m.extracted_skill 
			AND s.standardized_skill = ss.standardized_skill
			AND s.load_run_id = @load_run_id
	);
	
	PRINT '• Stale skill mentions:         ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';
	

	-- Delete skill mentions whose mappings have become invalid --
	DELETE m 
	FROM core.skill_mentions AS m
	JOIN core.job_postings AS j
		ON m.job_posting_id = j.job_posting_id
	JOIN core.standardized_skills AS ss
		ON m.standardized_skill_id = ss.standardized_skill_id
	WHERE EXISTS (
		SELECT 1 
		FROM staging.standardized_raw_skills AS s
		WHERE s.job_id = j.job_id 
			AND s.extracted_skill = m.extracted_skill
			AND s.standardized_skill = ss.standardized_skill 
			AND s.load_run_id = @load_run_id
			AND s.valid_mapping = 0
	)
	-- Edge case defense:
	-- The same skill phrase in a job posting could be extracted both as a hard and a soft skill, 
	-- while being mapped to the same standardized skill. These mappings converge into a single core 
	-- record, as the unique key (job_id, extracted_skill, standardized_skill) does not include 
	-- observed_skill_type. If one mapping becomes invalid but the other remains valid, the core record 
	-- must be preserved.
	-- Example:
	-- job_id, extracted_skill, observed_skill_type, standardized_skill, valid_mapping
	-- JP_10, Excel, soft, Microsoft Excel, 0 
	-- JP_10, Excel, hard, Microsoft Excel, 1 
	-- Result: "JP_10, Excel, Microsoft Excel" is preserved in core.
	AND NOT EXISTS (
		SELECT 1 
		FROM staging.standardized_raw_skills AS s
		WHERE s.job_id = j.job_id 
			AND s.extracted_skill = m.extracted_skill
			AND s.standardized_skill = ss.standardized_skill 
			AND s.load_run_id = @load_run_id
			AND s.valid_mapping = 1 
	);

	PRINT '• Invalid skill mentions:       ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	-- Delete skill mentions that reference stale standardized skills --
	DELETE m 
	FROM core.skill_mentions AS m
	JOIN #stale_standardized_skills AS s
		ON m.standardized_skill_id = s.standardized_skill_id;
	
	PRINT '• Stale standardized skills:    ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	-- Delete skill mentions that reference invalid standardized skills --
	DELETE m 
	FROM core.skill_mentions AS m
	JOIN #invalid_standardized_skills AS s
		ON m.standardized_skill_id = s.standardized_skill_id;

	PRINT '• Invalid standardized skills:  ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	/* ======================== */
	/* SYNCHRONIZE JOB POSTINGS */
	/* ======================== */

	PRINT CHAR(10) + CHAR(13) + 'Synchronizing job postings...';

	-- Delete orphaned job postings --
	DELETE j
	FROM core.job_postings AS j
	JOIN #orphaned_job_postings AS o
		ON j.job_posting_id = o.job_posting_id;

	PRINT '• Orphaned job postings:        ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	/* ===================== */
	/* SYNCHRONIZE COMPANIES */
	/* ===================== */

	PRINT CHAR(10) + CHAR(13) + 'Synchronizing companies...';

	-- Delete orphaned companies
	DELETE c
	FROM core.companies AS c
	WHERE NOT EXISTS (
		SELECT 1 
		FROM staging.job_posting_metadata AS s
		WHERE s.company = c.company
			AND s.load_run_id = @load_run_id	-- Latest staging load
	);

	
	PRINT '• Orphaned companies:           ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	/* ===================== */
	/* SYNCHRONIZE LOCATIONS */
	/* ===================== */

	PRINT CHAR(10) + CHAR(13) + 'Synchronizing locations...';

	-- Delete orphaned locations --
	DELETE l 
	FROM core.locations AS l
	WHERE NOT EXISTS (
		SELECT 1
		FROM staging.job_posting_metadata AS s
		WHERE s.city = l.city
			AND ISNULL(s.region, '') = ISNULL(l.region, '')
			AND s.country = l.country
			AND s.load_run_id = @load_run_id	-- Latest staging load
	);

	PRINT '• Orphaned locations:           ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';
	

	/* =============================== */
	/* SYNCHRONIZE STANDARDIZED SKILLS */
	/* =============================== */
	
	PRINT CHAR(10) + CHAR(13) + 'Synchronizing standardized skills...';

	-- Delete stale standardized skills
	DELETE c
	FROM core.standardized_skills AS c
	JOIN #stale_standardized_skills AS s
		ON c.standardized_skill_id = s.standardized_skill_id;
	
	PRINT '• Stale standardized skills:    ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	-- Delete invalid standardized skills (valid_standardized_skill or valid_classification = FALSE)
	DELETE c
	FROM core.standardized_skills AS c
	JOIN #invalid_standardized_skills AS s
		ON c.standardized_skill_id = s.standardized_skill_id;
	
	PRINT '• Invalid standardized skills:  ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';
	
	/* ================================= */
	/* SYNCHRONIZE SKILL CLASSIFICATIONS */
	/* ================================= */

	PRINT CHAR(10) + CHAR(13) + 'Synchronizing skill classifications...';

	-- Delete orphaned skill classifications
	DELETE c 
	FROM core.skill_classifications AS c
	WHERE NOT EXISTS (
		SELECT 1
		FROM staging.skill_classifications AS s
		WHERE s.skill_type = c.skill_type
			AND ISNULL(s.skill_category, '') = ISNULL(c.skill_category, '')
			AND ISNULL(s.skill_subcategory, '') = ISNULL(c.skill_subcategory, '')
			AND s.load_run_id = @load_run_id	-- Latest staging load
	);

	PRINT '• Orphaned classifications:     ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' deleted';


	PRINT(CHAR(13))
	RAISERROR ('==========================================', 0, 1) WITH NOWAIT;
	RAISERROR ('Load data into core tables', 0, 1) WITH NOWAIT;
	RAISERROR ('==========================================', 0, 1) WITH NOWAIT;


	/* ======================== */
	/* LOAD COMPANIES TABLE     */
	/* ======================== */

	INSERT INTO core.companies (
		company
	)
	SELECT DISTINCT
		s.company
	FROM staging.job_posting_metadata AS s
	LEFT JOIN core.companies AS c
		ON s.company = c.company
	WHERE c.company_id IS NULL
		AND s.load_run_id = @load_run_id;

	PRINT CHAR(10) + 'Companies:                      ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';
	

	/* ========================== */
	/* LOAD LOCATIONS TABLE       */
	/* ========================== */

	INSERT INTO core.locations (
		city,
		region,
		country
	)
	SELECT DISTINCT
		s.city,
		s.region,
		s.country
	FROM staging.job_posting_metadata AS s
	LEFT JOIN core.locations AS l
		ON s.city = l.city 
		AND ISNULL(s.region, '') = ISNULL(l.region, '') 
		AND s.country = l.country
	WHERE 
		l.location_id IS NULL
		AND s.load_run_id = @load_run_id;

	PRINT CHAR(10) + 'Locations:                      ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';


	/* ============================= */
	/* LOAD JOB POSTINGS TABLE        */
	/* ============================= */

	INSERT INTO core.job_postings (
		job_id,
		job_title,
		company_id,
		location_id,
		source_platform,
		original_URL,
		date_collected
	)
	SELECT 
		s.job_id,
		s.job_title,
		c.company_id,
		l.location_id,
		s.source_platform,
		s.original_URL,
		s.date_collected
	FROM staging.job_posting_metadata AS s
	JOIN core.companies AS c 
		ON s.company = c.company
	JOIN core.locations AS l 
		ON s.city = l.city 
		AND ISNULL(s.region, '') = ISNULL(l.region, '') 
		AND s.country = l.country
	LEFT JOIN core.job_postings AS j
		ON s.job_id = j.job_id
	WHERE
		j.job_posting_id IS NULL
		AND s.load_run_id = @load_run_id;

	PRINT CHAR(10) + 'Job postings:                   ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';


	/* ======================================= */
	/* LOAD SKILL CLASSIFICATIONS TABLE        */
	/* ======================================= */

	INSERT INTO core.skill_classifications (
		skill_type,
		skill_category,
		skill_subcategory
	)
	SELECT DISTINCT
		s.skill_type,
		s.skill_category,
		s.skill_subcategory
	FROM
		staging.skill_classifications AS s
	LEFT JOIN core.skill_classifications AS c
		ON s.skill_type = c.skill_type
		AND ISNULL(s.skill_category, '') = ISNULL(c.skill_category, '')
		AND ISNULL(s.skill_subcategory, '') = ISNULL(c.skill_subcategory, '')
	WHERE
		c.skill_classification_id IS NULL
		AND s.load_run_id = @load_run_id;

	
	PRINT CHAR(10) + 'Skill classifications:          ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';


	/* ===================================== */
	/* LOAD STANDARDIZED SKILLS TABLE        */
	/* ===================================== */

	INSERT INTO core.standardized_skills (
		standardized_skill,
		skill_classification_id
	)
	SELECT DISTINCT
		t.standardized_skill,
		c.skill_classification_id
	FROM
		staging.skill_taxonomy AS t
	JOIN core.skill_classifications AS c
		ON t.skill_type = c.skill_type 
		AND ISNULL(t.skill_category, '') = ISNULL(c.skill_category, '') 
		AND ISNULL(t.skill_subcategory, '') = ISNULL(c.skill_subcategory, '')
	LEFT JOIN core.standardized_skills AS s
		ON t.standardized_skill = s.standardized_skill
	WHERE 
		t.valid_standardized_skill = 1 
		AND t.valid_classification = 1
		AND s.standardized_skill_id IS NULL
		AND t.load_run_id = @load_run_id;


	PRINT CHAR(10) + 'Standardized skills:            ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';


	/* ================================= */
	/* LOAD SKILL MENTIONS TABLE         */
	/* ================================= */

	INSERT INTO core.skill_mentions (
		job_posting_id,
		extracted_skill,
		standardized_skill_id
	)
	SELECT DISTINCT
		j.job_posting_id,
		r.extracted_skill,
		s.standardized_skill_id
	FROM
		staging.standardized_raw_skills AS r
	JOIN core.job_postings AS j
		ON r.job_id = j.job_id
	JOIN core.standardized_skills AS s
		ON r.standardized_skill = s.standardized_skill
	LEFT JOIN core.skill_mentions AS c
		ON j.job_posting_id = c.job_posting_id 
		AND r.extracted_skill = c.extracted_skill
		AND s.standardized_skill_id = c.standardized_skill_id
	WHERE 
		r.valid_mapping = 1
		AND c.skill_mention_id IS NULL
		AND r.load_run_id = @load_run_id;

	PRINT CHAR(10) + 'Skill mentions:                 ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' inserted';


	COMMIT TRANSACTION;

	PRINT(CHAR(13))
	PRINT '==========================================';
	PRINT 'Successfully loaded all core tables.';
	PRINT 'Load run ID: ' + CHAR(13) +
		  CAST(@load_run_id AS VARCHAR(36));
	PRINT '==========================================';


END TRY
BEGIN CATCH
	
	PRINT 'Load failed. Rolling back transaction.';

	IF @@TRANCOUNT > 0
		ROLLBACK TRANSACTION;

	THROW;


END CATCH;




