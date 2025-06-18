select count(*) Pending from apps.FND_CONC_REQ_SUMMARY_V
 WHERE 1=1
   and phase_code = 'P'
   and phase_code||status_code||hold_flag||queue_method_code not in ('PQNB','PIYI','PQYB')
and trunc(REQUESTED_START_DATE) < trunc(SYSDATE+1);
