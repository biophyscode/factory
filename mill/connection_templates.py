#!/usr/bin/env python

"""
Template connection files for the factory.
"""

template_default = """

project:
  enable: true 
  development: true
  site: site/PROJECT_NAME  
  calc: calc/PROJECT_NAME
  repo: calc/PROJECT_NAME/calcs
  database: data/PROJECT_NAME/db.factory.sqlite3
  # locate a gromacs.py to use current machine gromacs configuration (can be null)
  omni_gromacs_config: null
  post_data_spot: data/PROJECT_NAME/post
  post_plot_spot: data/PROJECT_NAME/plot
  workspace_spot: data/PROJECT_NAME/workspace 
  # new simulations and automacs documentation reside in the simulation spot
  simulation_spot: data/PROJECT_NAME/sims
  # set a custom gromacs_config (~/.automacs.py) via: `gromacs_config: gromacs_config.py`
  # import previous data or point omnicalc to new simulations, each of which is called a "spot"
  spots:
    # colloquial name for the default "spot" for new simulations given as simulation_spot above
    sims:
      # name downstream postprocessing data according to the spot name (above) and simulation folder (top)
      # note: that namer is set by default to take a simulation number and save "e.g. v1000.my_calc.dat"
      # hint: if you have multiple spots then you *must* use spot in the namer or you violate uniqueness
      namer: "lambda spot,top : 'v'+re.findall('simulation-v([0-9]+)',top)[0]"
      # parent location of the spot_directory (may be changed if you mount the data elsewhere)
      route_to_data: data/PROJECT_NAME
      # path of the parent directory for the simulation data
      # note: that omnicalc joins route_to_data and spot_directory only propagates this information via namer
      # hint: this means that you can move the data but make sure namer doesn't lose track of the spot
      spot_directory: sims
      # rules for parsing the data in the spot directories
      regexes:
        # each simulation folder in the spot directory must match the top regex
        top: '(simulation-v[0-9]+)'
        # each simulation folder must have trajectories in subfolders that match the step regex (can be null)
        # note: you must enforce directory structure here with not-slash
        step: '([stuv])([0-9]+)-([^\/]+)'
        # each part regex is parsed by omnicalc
        part: 
          xtc: 'md\.part([0-9]{4})\.xtc'
          trr: 'md\.part([0-9]{4})\.trr'
          edr: 'md\.part([0-9]{4})\.edr'
          tpr: 'md\.part([0-9]{4})\.tpr'
          # specify a "structure" part for get_last_start_structure
          structure: '(system|system-input|structure)\.(gro|pdb)'

"""

template_demo = """

demo:
  enable: true 
  development: true
  site: site/PROJECT_NAME  
  calc: calc/PROJECT_NAME
  repo: calc/PROJECT_NAME/calcs
  database: data/PROJECT_NAME/db.factory.sqlite3
  post_data_spot: data/PROJECT_NAME/post
  post_plot_spot: data/PROJECT_NAME/plot
  simulation_spot: data/PROJECT_NAME/sims
  public:
    port: 2000
    notebook_port: 2001
    notebook_ip: 'green.seas.upenn.edu'
    hostnames: ['green.seas.upenn.edu']
    user: ryb
    group: users
    credentials: {'talking':'heads'}

"""