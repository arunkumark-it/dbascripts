set pagesize 40;
col object_name format a25;
col ora_user    format a10;
col os_user     format a10;
col c.sid     format 9999;
select  C.SID, serial#, B.object_name, oracle_username ORA_USER, os_user_name OS_USER,
decode(locked_mode,1,'NULL',2,'ROW-S',3,'ROW-X',4,'SHARE',5,'SHAREX',6,'EXCL') LMODE
from gV$locked_object A, dba_objects B, gv$session C where   A.object_id = B.object_id
and A.process  =  C.process
and b.object_name = upper('&object_name')
and b.owner = upper('&owner')
order by C.SID, serial#; 
