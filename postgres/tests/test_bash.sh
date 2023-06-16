x=0
while [ $x -le 100 ]; 
do 
    ddev test postgres:py3.9-14.0 -k test_statement_samples_collect[dd_admin-dd_admin-dogs-SELECT * FROM breed WHERE name = %s-Labrador-None-None-not_truncated-expected_warnings1-pg_stat_activity] --skip-env
    ((x++))
done