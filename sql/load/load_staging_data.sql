USE JobPostingsAnalysis_Demo;
GO

BEGIN TRY
	
	BEGIN TRANSACTION;

	DECLARE @load_run_id UNIQUEIDENTIFIER = NEWID();
	PRINT 'Starting load: ' + CONVERT(NVARCHAR(36), @load_run_id);

	/* ------------------------------------ */
	/* LOAD STANDARDIZED RAW SKILLS DATASET */
	/* ------------------------------------ */

	PRINT CHAR(13) + 'Loading standardized raw skills dataset...';

	DROP TABLE IF EXISTS staging.standardized_raw_skills_import_temp;

	-- Temporary table for importing the standardized raw skills dataset
	CREATE TABLE staging.standardized_raw_skills_import_temp (
		job_id NVARCHAR(20),
		extracted_skill NVARCHAR(255),
		observed_skill_type NVARCHAR(20),
		preliminary_skill NVARCHAR(255),
		standardized_skill NVARCHAR(255),
		valid_mapping NVARCHAR(10),
		error_message NVARCHAR(255)
	);

	BULK INSERT staging.standardized_raw_skills_import_temp
	FROM 'C:\Users\Sophia\OneDrive\Job_Postings_Analysis\data\extracted_demo\raw_to_standardized_skills.csv'
	WITH (
		FORMAT = 'CSV',
		FIRSTROW = 2,
		FIELDTERMINATOR = ',',
		ROWTERMINATOR = '\n',
		CODEPAGE = '65001'
	);

	-- Load temporary table data into staging table
	INSERT INTO staging.standardized_raw_skills(
		job_id,
		extracted_skill,
		observed_skill_type,
		preliminary_skill,
		standardized_skill,
		valid_mapping,
		error_message,
		load_run_id
	) 
	SELECT
		job_id,
		extracted_skill,
		observed_skill_type,
		preliminary_skill,
		standardized_skill,
	
		CASE 
			WHEN UPPER(TRIM(valid_mapping)) = 'TRUE' then 1
			WHEN UPPER(TRIM(valid_mapping)) = 'FALSE' then 0
			ELSE NULL
		END,

		error_message,
		@load_run_id
	FROM staging.standardized_raw_skills_import_temp;

	-- Drop temporary import table
	DROP TABLE IF EXISTS staging.standardized_raw_skills_import_temp;


	/* --------------------------- */
	/* LOAD SKILL TAXONOMY DATASET */
	/* --------------------------- */

	PRINT CHAR(13) + 'Loading skill taxonomy dataset...';

	DROP TABLE IF EXISTS staging.skill_taxonomy_import_temp;

	-- Temporary table for importing the skill taxonomy dataset
	CREATE TABLE staging.skill_taxonomy_import_temp (
		standardized_skill NVARCHAR(255),
		skill_type NVARCHAR(255),
		skill_category NVARCHAR(255),
		skill_subcategory NVARCHAR(255),
		valid_standardized_skill NVARCHAR(10),
		valid_classification NVARCHAR(10),	
		error_message NVARCHAR(255)
	);


	BULK INSERT staging.skill_taxonomy_import_temp
	FROM 'C:\Users\Sophia\OneDrive\Job_Postings_Analysis\data\extracted_demo\skill_taxonomy.csv'
	WITH (
		FORMAT = 'CSV',
		FIRSTROW = 2,
		FIELDTERMINATOR = ',',
		ROWTERMINATOR = '\n',
		CODEPAGE = '65001'
	);


	-- Load temporary table data into staging table
	INSERT INTO staging.skill_taxonomy(
		standardized_skill,
		skill_type,
		skill_category,
		skill_subcategory,
		valid_standardized_skill,
		valid_classification,	
		error_message, 
		load_run_id
	) 
	SELECT
		standardized_skill,
		skill_type,
		skill_category,
		skill_subcategory,
	
		-- Convert validation flags from CSV text to BIT
		CASE 
			WHEN UPPER(TRIM(valid_standardized_skill)) = 'TRUE' then 1
			WHEN UPPER(TRIM(valid_standardized_skill)) = 'FALSE' then 0
			ELSE NULL
		END,

		CASE 
			WHEN UPPER(TRIM(valid_classification)) = 'TRUE' then 1
			WHEN UPPER(TRIM(valid_classification)) = 'FALSE' then 0
			ELSE NULL
		END,

		error_message,
		@load_run_id
	FROM staging.skill_taxonomy_import_temp;

	-- Drop temporary import table
	DROP TABLE IF EXISTS staging.skill_taxonomy_import_temp;


	/* --------------------------------- */
	/* LOAD SKILL CLASSIFICATIONS DATASET */
	/* --------------------------------- */

	PRINT CHAR(13) + 'Loading skill classifications dataset...';

	DROP TABLE IF EXISTS staging.skill_classifications_import_temp;

	-- Temporary table for importing the skill classifications dataset
	CREATE TABLE staging.skill_classifications_import_temp (
		skill_type NVARCHAR(255),
		skill_category NVARCHAR(255),
		skill_subcategory NVARCHAR(255)
	);

	BULK INSERT staging.skill_classifications_import_temp
	FROM 'C:\Users\Sophia\OneDrive\Job_Postings_Analysis\data\extracted_demo\skill_classifications.csv'
	WITH (
		FORMAT = 'CSV',
		FIRSTROW = 2,
		FIELDTERMINATOR = ',',
		ROWTERMINATOR = '\n',
		CODEPAGE = '65001'
	);


	-- Load temporary table data into staging table
	INSERT INTO staging.skill_classifications(
		skill_type,
		skill_category,
		skill_subcategory,
		load_run_id
	) 
	SELECT
		skill_type,
		skill_category,
		skill_subcategory,
		@load_run_id
	FROM staging.skill_classifications_import_temp;

	-- Drop temporary import table
	DROP TABLE IF EXISTS staging.skill_classifications_import_temp;


	/* --------------------------------- */
	/* LOAD JOB POSTING METADATA DATASET */
	/* --------------------------------- */

	PRINT CHAR(13) + 'Loading job posting metadata dataset...';

	DROP TABLE IF EXISTS staging.job_posting_metadata_import_temp;

	-- Temporary table for importing the job posting metadata dataset
	CREATE TABLE staging.job_posting_metadata_import_temp (
		job_id NVARCHAR(255),
		company NVARCHAR(255),
		job_title NVARCHAR(255),
		location NVARCHAR(255),
		source_platform NVARCHAR(255),
		original_url NVARCHAR(1000),
		date_collected DATE,
		city NVARCHAR(255),
		region NVARCHAR(255),
		country NVARCHAR(255)
	);

	BULK INSERT staging.job_posting_metadata_import_temp
	FROM 'C:\Users\Sophia\OneDrive\Job_Postings_Analysis\data\extracted_demo\extracted_job_posting_metadata.csv'
	WITH (
		FORMAT = 'CSV',
		FIRSTROW = 2,
		FIELDTERMINATOR = ',',
		ROWTERMINATOR = '\n',
		CODEPAGE = '65001'
	);


	-- Load temporary table data into staging table
	INSERT INTO staging.job_posting_metadata(
		job_id,
		company,
		job_title,
		location,
		city,
		region,
		country,
		source_platform,
		original_url,
		date_collected,
		load_run_id
	) 
	SELECT
		job_id,
		company,
		job_title,
		location,
		city,
		region,
		country,
		source_platform,
		original_url,
		date_collected,
		@load_run_id
	FROM staging.job_posting_metadata_import_temp;

	-- Drop temporary import table
	DROP TABLE IF EXISTS staging.job_posting_metadata_import_temp;
	
	COMMIT TRANSACTION;

	PRINT CHAR(13) + 
		'Successfully loaded all staging tables. Load ID: ' +
		CONVERT(NVARCHAR(36), @load_run_id); 

END TRY
BEGIN CATCH
	
	PRINT 'Load failed. Rolling back transaction.';

    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;

END CATCH;

GO
