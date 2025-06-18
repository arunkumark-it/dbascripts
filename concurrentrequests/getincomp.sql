
SELECT fsrn.program,
         fsrn.request_id,
         -- fstr.concurrent_program_id,
         fstr.program  incompatible_program,
         fstr.request_id incompatible_prog_req_id,
         (SELECT meaning
            FROM apps.fnd_lookups
           WHERE     lookup_type = 'CP_PHASE_CODE'
                 AND lookup_code = fstr.phase_code)
            phase,
         (SELECT meaning
            FROM apps.fnd_lookups
           WHERE     lookup_type = 'CP_STATUS_CODE'
                 AND lookup_code = fstr.status_code)
            status,
         ROUND (
            (fstr.actual_completion_date - fstr.actual_start_date) * 24 * 60,
            2)
            time_taken_minutes,
         DECODE (
            fstr.actual_completion_date,
            NULL, ROUND ( (SYSDATE - fstr.actual_start_date) * 24 * 60, 2))
            running_for_minutes
    FROM apps.fnd_concurrent_program_serial fcs,
         apps.fnd_conc_req_summary_v      fstr,
         apps.fnd_conc_req_summary_v      fsrn
   WHERE     1 = 1                   -- running_concurrent_program_id = 123123
       AND fsrn.request_id = 168650388 --Request id which is in standby status
         --AND fsrn.program = ''      --Or concurrent program name which is in standby status
         AND to_run_concurrent_program_id = fstr.concurrent_program_id
         AND running_concurrent_program_id = fsrn.concurrent_program_id
         AND (   fstr.requested_start_date > fsrn.requested_start_date
              OR fstr.actual_completion_date IS NULL)
         AND fsrn.phase_code = 'P'     --Pending
         AND fstr.status_code != 'D'   -- not cancelled
ORDER BY fstr.request_id DESC;
