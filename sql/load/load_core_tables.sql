USE JobPostingsAnalysis;
GO

BEGIN TRY
	
	BEGIN TRANSACTION;

	/* ================================= */
	/* TRANSFORM COMPANY DIMENSION       */
	/* ================================= */

	INSERT INTO core.companies (
		company
	)
	SELECT DISTINCT
		s.company
	FROM staging.job_posting_metadata AS s
	LEFT JOIN core.companies AS c
		ON s.company = c.company
	WHERE c.company_id IS NULL;


	/* ================================= */
	/* TRANSFORM LOCATION DIMENSION      */
	/* ================================= */

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
		l.location_id IS NULL;


	/* ================================= */
	/* TRANSFORM JOB POSTING DIMENSION   */
	/* ================================= */

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
		j.job_posting_id IS NULL;


	/* ========================================== */
	/* TRANSFORM SKILL CLASSIFICATION DIMENSION   */
	/* ========================================== */

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
		c.skill_classification_id IS NULL;


	/* ======================================== */
	/* TRANSFORM STANDARDIZED SKILL DIMENSION   */
	/* ======================================== */

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
		AND s.standardized_skill_id IS NULL;


	/* ==================================== */
	/* TRANSFORM SKILL MENTION FACT TABLE   */
	/* ==================================== */

	INSERT INTO core.skill_mentions (
		job_posting_id,
		extracted_skill,
		observed_skill_type,
		standardized_skill_id
	)
	SELECT DISTINCT
		j.job_posting_id,
		r.extracted_skill,
		r.observed_skill_type,
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
		AND r.observed_skill_type = c.observed_skill_type
	WHERE 
		r.valid_mapping = 1
		AND c.job_posting_id IS NULL;


	COMMIT TRANSACTION;

END TRY
BEGIN CATCH
	
	PRINT 'Transform/load failed. Rolling back transaction.';

	IF @@TRANCOUNT > 0
		ROLLBACK TRANSACTION;

	THROW;


END CATCH;




