# Legacy development Setup

To get started developing with the integrations-core repo you will need: `gem`
and `python`.

We’ve written a gem and a set of scripts to help you get set up, ease development,
and provide testing. To begin:

- Run `gem install bundler`
- Run `bundle install`

Once the required Ruby gems have been installed by Bundler, you can easily create
a Python environment:

- Run `rake setup_env`. This will install a Python virtual environment along
  with all the components necessary for integration development (including the
  core agent used by the integrations). Some basic software might be needed to
  install the python dependencies like `gcc` and `libssl-dev`.
- Run `source venv/bin/activate` to activate the installed Python virtual
  environment. To exit the virtual environment, run `deactivate`. You can learn
  more about the Python virtual environment on the Virtualenv documentation.

This is a quick setup but from that point you should be able to run the default
test suit `rake ci:run`.
To go beyond we advise you to read the full documentation [here](https://docs.datadoghq.com/developers/integrations/integration_sdk/).
