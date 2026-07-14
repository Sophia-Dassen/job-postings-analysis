
CREATE DATABASE JobPostingsAnalysis_Demo;
GO

USE JobPostingsAnalysis_Demo;
GO

:r schema/create_schemas.sql

:r schema/staging/create_staging_tables.sql

:r schema/core/create_core_tables.sql

:r load/load_staging_data.sql

:r load/load_core_tables.sql

GO
