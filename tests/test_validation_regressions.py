import json,pytest
from evaldrift.power import paired_test,is_claim_supportable
from evaldrift.cli import main

def test_low_planning_power_does_not_disprove_observed_significance():
 assert not is_claim_supportable(8/198,198)[0]
 observed=paired_test(8,0,198)
 assert observed['p_value']==pytest.approx(2/256)
 assert observed['significant']

def test_no_discordance_and_invalid_counts():
 assert paired_test(0,0,100)['p_value']==1
 for a in [(-1,0,100),(4,6,9),(1.5,0,10)]:
  with pytest.raises(ValueError):paired_test(*a)

def test_paired_cli(capsys):
 assert main(['paired','--gained','8','--lost','0','--total','198'])==0
 assert json.loads(capsys.readouterr().out)['significant']
