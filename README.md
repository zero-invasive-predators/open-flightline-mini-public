# open-flightline-mini
Open Flightline project based on single user and geopackage data storage


## Installing and Configuration
Although this toolset will work on most versions of QGIS, it is suggested that QGIS 3.34 is used.

1.	Download or clone a copy of the repo from here: https://github.com/zero-invasive-predators/open-flightline-mini
2.	Open up QGIS and go to the File Menu, then to Settings then to Options.
3.	In the Options dialog box, go to the Processing tab.
4.	Expand out the Scripts Setting and click the three dots to edit the Value
5.	Add two records that point to the repo directory location and the open_flightline_mini module:
example:
- C:/Users/user_name/Documents/GitHub/open-flightline-mini-public
- C:/Users/user_name/Documents/GitHub/open-flightline-mini-public/open_flightline_mini
- Note: If the project is going to be saved somewhere different, then each of the python files in the processing_tools folder need to have the repo_path variable updated. This is near the top of each file with the import statements
6. Click Ok, and Ok.
7. Now in the processing toolbox under the Scripts section, the Open Flightline Mini tools should appear.

## Documentation

See the Doccumentation folder for instructions on running each of the tools


## Important Notes:
- To reduce the amount of code and simplify the processing tools, I had tried to use the @alg decorator.
However, processing algorithims written in this way meant that the python modules and default values were
calculated on the map project startup instead of each run of the tool. So in the meantime, the older full style
of processing algorithims are used.
