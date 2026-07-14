USE JobPostingsAnalysis_Demo;
GO

CREATE SCHEMA core;
GO

CREATE TABLE core.companies (
	company_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	company NVARCHAR(255) NOT NULL UNIQUE
);


CREATE TABLE core.locations (
	location_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	city NVARCHAR(255),
	region NVARCHAR(255),
	country NVARCHAR(255) NOT NULL,
	CONSTRAINT uq_location UNIQUE (city, region, country)
);


CREATE TABLE core.job_postings (
	job_posting_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	job_id NVARCHAR(20) NOT NULL UNIQUE,
	job_title NVARCHAR(255) NOT NULL,
	company_id INT NOT NULL FOREIGN KEY REFERENCES core.companies(company_id),
	location_id INT NOT NULL FOREIGN KEY REFERENCES core.locations(location_id),
	source_platform NVARCHAR(255),
	original_URL NVARCHAR(500),
	date_collected DATE,
	created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
	updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);


CREATE TABLE core.skill_classifications (
	skill_classification_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	skill_type NVARCHAR(20) NOT NULL,
	skill_category NVARCHAR(255),
	skill_subcategory NVARCHAR(255),
	CONSTRAINT valid_skill_type CHECK (skill_type IN ('hard', 'soft')),
	CONSTRAINT uq_skill_classification UNIQUE (skill_type, skill_category, skill_subcategory)
);


CREATE TABLE core.standardized_skills (
	standardized_skill_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	standardized_skill NVARCHAR(255) NOT NULL UNIQUE,
	skill_classification_id INT NOT NULL REFERENCES core.skill_classifications(skill_classification_id)
);



CREATE TABLE core.skill_mentions (
	skill_mention_id INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
	job_posting_id INT NOT NULL FOREIGN KEY REFERENCES core.job_postings(job_posting_id),
	extracted_skill NVARCHAR(255) NOT NULL,
	observed_skill_type NVARCHAR(20) NOT NULL,
	standardized_skill_id INT FOREIGN KEY REFERENCES core.standardized_skills(standardized_skill_id),
	created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
	updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
	CONSTRAINT uq_skill_extraction UNIQUE (job_posting_id, extracted_skill, observed_skill_type)
);

GO
