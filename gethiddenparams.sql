 set head on feed on verify off
set linesize 300
col Instance_Value format a30
col Session_Value format a30
col Parameter format a45
SELECT
a.ksppinm "Parameter",
b.ksppstvl "Session_Value",
c.ksppstvl "Instance_Value"
FROM
x$ksppi a,
x$ksppcv b,
x$ksppsv c
WHERE
a.indx = b.indx
AND
a.indx = c.indx
AND
a.ksppinm LIKE '/_%' escape '/'
and a.ksppinm like '%&A%';
