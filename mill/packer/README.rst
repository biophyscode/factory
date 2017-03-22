=========
Simulator
=========

A simple package which runs biophysics molecular dynamics simulations using GROMACS.
Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Add "simulator" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'simulator',
    ]

2. Include the polls URLconf in your project urls.py like this::

    url(r'^simulator/',include('simulator.urls')),

3. Run `python manage.py migrate` to create the polls models.

4. Visit http://127.0.0.1:8000/simulator/ to make new simulations.