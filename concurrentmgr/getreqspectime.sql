SELECT *
FROM fnd_conc_req_summary_v
WHERE requested_start_date BETWEEN TO_DATE('2025-08-31 00:02:00', 'YYYY-MM-DD HH24:MI:SS') 
                               AND TO_DATE('2025-08-31 02:02:00', 'YYYY-MM-DD HH24:MI:SS');
