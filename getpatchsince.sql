SELECT * FROM ( select ap.patch_name, decode(MERGED_DRIVER_FLAG, 'Y', ad_pa_validate_criteriaset.get_concat_mergepatches (pd.patch_driver_id ), ''), 
max(at.name), l.language, ap.applied_patch_id, pr.appl_top_id, count(*) DRIVERS_APPLIED, to_char(max(end_date), 'dd-MM-yyyy hh24:mi:ss') COMPLETION_DATE,
 max(end_date), pd.patch_driver_id PATCH_DRV_ID from ad_appl_tops at, ad_patch_driver_langs l, ad_patch_runs pr, ad_patch_drivers pd, ad_applied_patches ap
  where pr.appl_top_id = at.appl_top_id AND at.APPLICATIONS_SYSTEM_NAME = '&SID' and pr.patch_driver_id = pd.patch_driver_id and pd.applied_patch_id = ap.applied_patch_id 
  and pd.patch_driver_id = l.patch_driver_id AND pr.start_date >= '&FROM_DATE' AND l.language in ( 'US') group by ap.applied_patch_id, ap.patch_name, pr.appl_top_id,
   decode(MERGED_DRIVER_FLAG, 'Y', ad_pa_validate_criteriaset.get_concat_mergepatches (pd.patch_driver_id ), ''), pd.patch_driver_id, l.language order by 9 desc, 1 desc, 2 desc, 3 desc, 4 desc ) 
   WHERE rownum < 1001
