for (( c=1; c<=100; c++ ))
do 
   ddev test postgres:py3.9-9.6 -k test_disabled_activity_or_explain_plans --skip-env
done