set verify off
set linesize 100
column PATCH_NUMBER format a12
column MODULE format a10
select ORIG_BUG_NUMBER PATCH_NUMBER,to_char(creation_date,'dd/mon/yyyy hh24:mi:ss') creation_date,
APPLICATION_SHORT_NAME MODULE 
from ad_patch_run_bugs
where ORIG_BUG_NUMBER='&Patch_Number'
