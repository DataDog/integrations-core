import pytest

from datadog_checks.dev.tooling.commands.validate.jmx_metrics import duplicate_bean_check, jmx_metrics

regular_beans = {
  "jmx_metrics": [
    {
      "include": {
        "attribute": {
          "Count": {
            "metric_type": "gauge", 
            "alias": "foo.bar"
          }
        }, 
        "bean": "my.bean:type=foo,name=baz"
      }
    }, 
    {
      "include": {
        "attribute": {
          "Rate": {
            "metric_type": "gauge", 
            "alias": "foo.bar"
          }
        }, 
        "bean": "my.bean:type=foo,name=baz"
      }
    }
  ]
}
duplicate_beans = {
  "jmx_metrics": [
    {
      "include": {
        "attribute": {
          "Count": {
            "metric_type": "gauge", 
            "alias": "foo.bar"
          }
        }, 
        "bean": "my.bean:type=foo,name=baz"
      }
    }, 
    {
      "include": {
        "attribute": {
          "Count": {
            "metric_type": "gauge", 
            "alias": "foo.bar"
          }
        }, 
        "bean": "my.bean:type=foo,name=baz"
      }
    }
  ]
}

@pytest.mark.parametrize(
    'beans,errors',
    [
        (regular_beans, 0),
        (duplicate_beans, 1),
    ],
)
def test_duplicate_beans(beans, errors):
    result = duplicate_bean_check(beans.get("jmx_metrics"))
    assert len(result) >= errors
