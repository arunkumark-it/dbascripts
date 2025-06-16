select fcq.concurrent_queue_name, fcq.user_concurrent_queue_name,fcp.last_update_date,
fcp.concurrent_process_id,flkup.meaning,fcp.logfile_name
FROM fnd_concurrent_queues_vl fcq, fnd_concurrent_processes fcp, fnd_lookups flkup
WHERE --fcq.concurrent_queue_name in ('WFMLRSVC','WFALSNRSVC','WFWSSVC')
fcq.concurrent_queue_id = fcp.concurrent_queue_id
AND fcq.application_id = fcp.queue_application_id
AND flkup.lookup_code=fcp.process_status_code
AND lookup_type ='CP_PROCESS_STATUS_CODE'
AND flkup.meaning='Active';
