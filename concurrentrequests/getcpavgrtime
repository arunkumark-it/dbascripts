select program, ROUND(AVG( run_time )) from (
SELECT
    program,
    actual_start_date,
    actual_completion_date,
    round(((actual_completion_date - actual_start_date) * 60 * 24), 2) run_time
FROM
    apps.fnd_conc_req_summary_v
WHERE
    round(((actual_completion_date - actual_start_date) * 60 * 24), 2) > 15
    and PROGRAM not in ('Cost Manager','Planning Manager','PO Output for Communication')
ORDER BY
    4 DESC) group by program;
