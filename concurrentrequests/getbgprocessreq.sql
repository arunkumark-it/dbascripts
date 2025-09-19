Select module, status, action, inst_id,sid, serial# from gv$session where paddr = (select addr from gv$process where spid = (select oracle_process_id from 
fnd_concurrent_requests where request_id = &a));
