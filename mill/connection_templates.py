#!/usr/bin/env python

"""
Template connection files for the factory. See `make help` for usage.
"""

template_demo = """

# FACTORY PROJECT (the base case example "demo")
demo:
  # include this project when reconnecting everything
  enable: true 
  site: site/PROJECT_NAME  
  calc: calc/PROJECT_NAME
  repo: http://github.com/biophyscode/omni-basic
  database: data/PROJECT_NAME/db.factory.sqlite3
  post_spot: data/PROJECT_NAME/post
  plot_spot: data/PROJECT_NAME/plot
  simulation_spot: data/PROJECT_NAME/sims
  public:
    port: 2000
    notebook_port: 2001
    notebook_ip: 'green.seas.upenn.edu'
    hostnames: ['green.seas.upenn.edu']
    user: ryb
    group: users
    credentials: {'super':'secret'}
  # import previous data or point omnicalc to new simulations, each of which is called a "spot"
  # note that prepared slices from other integrators e.g. NAMD are imported via post with no naming rules
  spots:
    # colloquial name for the default "spot" for new simulations given as simulation_spot above
    sims:
      # name downstream postprocessing data according to the spot name (above) and simulation folder (top)
      # the default namer uses only the name (you must generate unique names if importing from many spots)
      namer: "lambda name,spot: name"
      # parent location of the spot_directory (may be changed if you mount the data elsewhere)
      route_to_data: data/PROJECT_NAME
      # path of the parent directory for the simulation data
      spot_directory: sims
      # rules for parsing the data in the spot directories
      regexes:
        # each simulation folder in the spot directory must match the top regex
        top: '(.+)'
        # each simulation folder must have trajectories in subfolders that match the step regex (can be null)
        # note: you must enforce directory structure here with not-slash
        step: '([stuv])([0-9]+)-([^\/]+)'
        # each part regex is parsed by omnicalc
        part: 
          xtc: 'md\.part([0-9]{4})\.xtc'
          trr: 'md\.part([0-9]{4})\.trr'
          edr: 'md\.part([0-9]{4})\.edr'
          tpr: 'md\.part([0-9]{4})\.tpr'
          # specify a naming convention for structures to complement the trajectories
          structure: '(system|system-input|structure)\.(gro|pdb)'
"""
