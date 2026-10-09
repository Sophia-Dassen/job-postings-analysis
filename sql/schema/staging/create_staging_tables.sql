
CREATE TABLE staging.standardized_raw_skills (
	standardized_raw_skill_id INT IDENTITY(1,1) PRIMARY KEY,
	job_id NVARCHAR(20),
	extracted_skill NVARCHAR(255),
	observed_skill_type NVARCHAR(20),
	preliminary_skill NVARCHAR(255),
	standardized_skill NVARCHAR(255),
	valid_mapping BIT,
	error_message NVARCHAR(255),
	load_run_id UNIQUEIDENTIFIER NOT NULL,
	loaded_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);


CREATE TABLE staging.skill_taxonomy (
	skill_taxonomy_record_id INT IDENTITY(1,1) PRIMARY KEY,
	standardized_skill NVARCHAR(255),
    skill_type NVARCHAR(255),
    skill_category NVARCHAR(255),
    skill_subcategory NVARCHAR(255),
    valid_standardized_skill BIT,
    valid_classification BIT,	
    error_message NVARCHAR(255), 
	load_run_id UNIQUEIDENTIFIER NOT NULL,
	loaded_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE staging.skill_classifications(
	skill_classification_id INT IDENTITY(1,1) PRIMARY KEY,
	skill_type NVARCHAR(255),
	skill_category NVARCHAR(255),
	skill_subcategory NVARCHAR(255),
	load_run_id UNIQUEIDENTIFIER NOT NULL,
	loaded_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE staging.job_posting_metadata(
	job_posting_id INT IDENTITY(1,1) PRIMARY KEY,
	job_id NVARCHAR(255),
	company NVARCHAR(255),
	job_title NVARCHAR(255),
	location NVARCHAR(255),
	city NVARCHAR(255),
	region NVARCHAR(255),
	country NVARCHAR(255),
	source_platform NVARCHAR(255),
	original_url NVARCHAR(1000),
	date_collected DATE,
	load_run_id UNIQUEIDENTIFIER NOT NULL,
	loaded_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

GO
