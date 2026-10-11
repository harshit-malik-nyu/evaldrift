SELECT benchmark,items,mde,required,MAX(required-items,0) additional_items,CASE WHEN mde<=0.02 THEN 'meets planning target' ELSE 'underpowered for planning target' END planning_status FROM observations ORDER BY mde DESC,benchmark;
SELECT COUNT(*) benchmarks,SUM(mde<=0.02) meeting_target,AVG(mde) mean_mde FROM observations;
