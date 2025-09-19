COL index_owner FORMAT A10
column table_owner format a15
column table_name format A18
column index_name format A18
column column_name format A18
COL POS FORMAT 999

Select index_owner, table_name, index_name, column_name, column_position POS
FROM dba_ind_columns
Where index_owner='&owner_name'
AND table_name='&table_name' Order by index_NAME;
