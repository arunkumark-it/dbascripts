set verify off
set pagesize 24
set linesize 100
column application_name format a35
column application_short_name format a10 heading 'SHORT_NAME'
column product_version format a10 heading 'VERSION'
column status format a10
column patch_level format a10
select a.application_short_name,a.application_name,b.product_version,
       decode(b.status,'I','INSTALLED','S','SHARED','N/A') Status,b.patch_level
       from fnd_application_vl a, fnd_product_installations b
       where a.application_id=b.application_id
       and patch_level like '%&MODULE_SHORTNAME%'
