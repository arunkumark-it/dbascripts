set lines 300
col MACHINE format a15
col os_process a10
col owner format a10
col OSUSER format a10
col OBJECT_NAME format a25
col module format a20
col session_spec format a15
SELECT c.owner,c.object_name
      ,vs.machine
      ,vs.osuser
      ,vs.sid||','||vs.serial#||',@'||vs.inst_id session_spec,vs.LOGON_TIME
      ,vp.pid
      ,vp.spid AS db
      ,vs.status
      ,vs.module
      ,vs.process
FROM  gv$locked_object vlocked
    ,gv$process       vp
    ,gv$session       vs
    ,dba_objects     c
WHERE vs.sid = vlocked.session_id
AND vlocked.object_id = c.object_id
AND vs.paddr = vp.addr AND vs.inst_id=vp.inst_id
AND c.object_name LIKE '%' || upper('&1') || '%'
AND nvl(vs.status
      ,'XX') != 'KILLED';
