# ShipX guide

ShipX is a hydrodynamic workbench developed by **SINTEF Ocean**. Its purpose is to perform various types of calculations using the same vessel input. It includes plug-ins for advanced analyses such as seakeeping, wave resistance, vessel motions, stationkeeping, and more.

This guide walks through the full workflow, from creating your first task to obtaining results, explaining each options along the way. At the end, an example using the **CS-Voyager** as input is provided.

## Getting started

When you open ShipX for the first time, it will prompt to either select or create a new workspace, it is advice to create one workspace per project.\
Once you have created/selected your workspace, the main interface appears divided in four sections :
- **Navigation view** (top-left): Displays tasks in a hierarchical tree.
- **Error log** and **Progress view** (bottom-left): Show simulation issues and progress.
- **Graphics view** (upper-center): Displays graphics and 3D view of your model.
- **Editors** (lower-center): Where the editors/dialogs input are display.

## Creating your first ShipX task

A task contains the model and run settings. To create your first shipX task : 
1. Right click on the navigator view,
2. Select "New" → "ShipX Task". 

Congratulation, you just create your first ShipX task! 

Notice other task types are available for advanced use, but they are beyond this guide’s scope.

You now have created a worspace and a task, the next step is to configure the ship you want to study.

## Ship configuration
> In this section (and beyond), marin terms are used. If you are unfamiliar with them [this part](#marin-terms-definition) is dedicated to the definition of some of them, you can also do research by yourself.

### Hull geometry

#### Coordinate system
Before continuing, you must know how the coordinate system is define in ShipX. It's define the same way as a **"left-handed" coordinate system** (classic naval architecture system). The **$x$-axis** is poitning toward the stem with origin at the aft perpendicular (AP), the **$y$-axis** positive to starboard with origin at the centerline and the **$z$-axis** is pointing upward with origin at the baseline.

#### Create a ship
There are two way to add a ship :
1. **Creating it manually** : Right-click on the ShipX task then select "New" → "Ship". Anew folder name "Fleet" will appear with your new ship inside.
2. **Importing it** : Right-click anywhere on the navigation view and select "import". This window should come up :\
    ![import window](Pictures/ShipX%20view/import_window.png)

    Go inside the "*ShipX Geometry*" folder, now you see a list of geometry formats you can use to import hull informations : *.gf*, *.dra*, *.dxf*, *.shipx*, *.lin*, *.n2x*, *.shipx_ship*, *.mgf*.

**<ins>Remark</ins>** : Import a geometry file automatically creates a new ShipX task with the imported ship. So if you plan to import your ship don't start by creating a task, it will be done in the same time.

#### Stations
The hull shape is defined by a series of transverse sections ($yOz$ plan) along the length ($x$-axis), called **stations**. If you imported a hull geometry, the stations are automatically defined and you can skip this part. If you created a ship manually, you have to define the stations yourself. It's not recommanded because time-consumming but if you want to do it anyway here is how to proceed :\
1. Double-click the ship object in the task to **open the ship editor**, you should see the empty version of this :\
    ![Ship editor view](Pictures/ShipX%20view/stations.png)
    As you can see the editor is separate in two, with the list of stations and points inside on the left and a graphic representation on the right.\
2. Click on the green circle in the upper left section to **add a station** and define the $x$-position of the station.\
    If you don't know how many stations you should define, here is a tip : As an approxiamation, keep in mind the distance between 2 stations (we call $a$) must be 5 times shorter than the minimum investigated regular wave length ($\lambda$), or $a = \dfrac{\lambda}{5}$, with a maximum of 150 stations.\
3. Click on the green circle below the second table to **add points to the station** with $y$ and $z$ coordinate, and the **Point class**.\
    You can add up to 500 points, for this example only 4 points per stations are used.\
    You only
    <!-- -There are 6 classes : 
    - Point with no characteristics : 
    - Knuckle point : 
    - Tangency in : 
    - Tangency out : 
    - Defined by 3D line : 
    - Defined by contour : 
    -->
    
**<ins>Remark</ins>** : It's possible to perform operation on the table by clicking on the gear at the bottom right of a table.

Now your ship is here you can **see it in the 3D view**. To do this right-click on the ShipX task and select "View in 3D"

### Ship characteristics
Once the hull geometry is defined, set the characteristics of your ship :
- **Length overall (Loa) [m]** : Max ship's length;
- **length between perpendicular (Lpp) [m]** : Length from the center line axis of the rudder to the crossing point between the bow and the waterline;
- **Moulded depth (D) [m]** : Total depth from the deck to the hull's baseline;
- **Breadth overall (Boa) [m]** : Max ship's breadth;
- **Stem position (Aft) [m]** : Position of the ship's aftmost point of the hull.

Those are **essential** for the ship definition, if you imported the hull they are automatically filled but it's always a good thing to check.

It's also possible to give informations about the ship model like the model number, the model scale or the ship hull category.

Well done! You've defined the geometry of your hull. Let's go to the next step : the loading condition.

### Loading condition
Each ship includes a *Design Loading Condition* object. This stores key operational parameters for hydrostatics and stability calculations.

This is what the input of Loading condition data look like :\
![View of the Loading condition input](Pictures/ShipX%20view/loading_condition_input.png)
The fields in red are in "*read only*", so you can't modify them. Here is a description of the other data you can fill :
- **Draugth** (or **draft**) **[m]** : Heigth between the baseline of the hull and the waterline, link to the displacement (weight) of the ship. The most important among the loading condition data.
- **Trim [m]** : Difference between forward and after draught.
- **Angle of heel [deg]** : The angle between the vertical and the ship's centerline, it can be caused by wind or current.
- **Shell plating Thickness [mm]** : The thickness of the outer-most structure on the hull.
- **Shell plating in % of Displacement [%]** : The weight portion of the shell plating in the displacement.

#### Wind and Current sections
You've seen all the possibilities in the loading contion section, you could also notice there are three more sections : Wind, Current and Note (not important). **Wind** and **Current** are used to define the drag and lift coefficients of the ship in the wind and current.

### Additional features
For some simulation you may need to specify **additional features** in your ship like foils, moonpools or bilge keels. To **add them** right-click on the ship object, then select "New" and a list will appear. The picture below show the list of all the possible feature you can add to your ship if needed. Some of them will be detail further [here](#run-1).\
![List of possible ship features](Pictures/ShipX%20view/list_ship_feature.png)

With that last point, you've seen all the possible things to do when you define your ship from basic geometry to more advanced details.\
Your ship is now in ShipX and you can start the configuration of your run, the last step before executing it and have results.

## Configuring a run
To **create a new run** you just have to right-click on Design Loading condition and you should see a list of possible run (post processors only work with Veres, [see here](#post-processor)). Without considering the post processors, the runs can be split in two categories : 
1. **Independent** (Hullvisc run, Stationkeeping run, Veres run). 
2. **Dependent** (Combined run, Hull transformation run, Veres RAO generator run). Use the result of other run like Veres to calculate something, for exemple, Veres RAO generator run generate RAO files using the results of the Veres run.

### Veres
The VEssel RESponse plug-in **simulate the behavior** in a seaway to help evaluate performance and operability. Important ship's motions have a strong impact on the operability in a seaway, so the **study of wave induced vessel responses** can be essential in the ship design.\
This guide is only a condensed version of how to use Veres, if you want more information and details about Veres and how it works you can refer to [this document](Documents/Manuals/veres-user-manual.pdf) for the details and [this document](Documents/Fact_sheets/shipx_veres.pdf) for a global review.

Open the Veres run editor, you can see there are 6 differents tab, let's start with the first one : 'Main'.

#### Main
![veres editor main tab](Pictures/ShipX%20view/Veres/main_veres.png)

Start by selecting the **hull type** (Monohull, multihull). Then in the **Vessel Simulator** section you can decide wether you want or not to generate an input to the [Vessel Simlator](https://www.sintef.no/en/software/vesim/), another sofware developped by Sintef.\

---
The next section is about the vessel **Geometry** file created when Veres is ran, you can check *automatically generate a geometry file* and let Veres create and update a geometry file with the vessel you draw/import earlier or use yours. If you unchecked the box, two new options will appear asking you : the location of the geometry file (*.mgf*) and the vertical position of base line. Wether you check the box or not, you can specified the *number of interpolated offset-points* (max 80). Short reminder, the offset-points define the semi-section (stations) of the hull.

---
In **Calculation options** you can personalize the calculations you want ShipX to do by selecting, in a first time, the *calculation method* to use among :
- The Strip-theory formulation (2D ordinary) ;
- The Strip-theory formulation (2D direct pressure integration) ;
- The High-speed formulation (2.5D direct pressure integration) ;

Then, you choose to ignore or not the *mass balance check*, and to *apply motion limits*.\
Finally, you have the possiblity to calculate (if you want to) the *added resistance* using two different methods :
- Gerritsma & Beukelman
- Pressure integration

---
**Global loads** results from the interaction between the ship and its environment (waves, buoyancy, hydrostatic pressure, ...). They can cause hull deformation and are to be considered in the design of the hull to avoid big complications. Veres offer the possibility to calculate these loads, to do that check the box beside "*Calculate the global loads*", three more inputs show up.\
In first, the *type of mass distribution*, you have the choice between continuous mass distribution and discrete weights.
**Continuous mass distribution** means the mass is spread over the hull without distinction of each object. The **discrete weights** option takes into account the mass of each object located at a specific position (engines, tanks, ...). The weights are defined in the [Mass distribution](#mass-distribution) tab.\
In second, a check box "*Torsion moments*" .\
And the last one is *Cut sections*, here you have to select the transverse cut planes you want to use. To create transverse cut planes, right-click on your ship then select "New"→"Cut planes"→"Transverse Cuts", under "Design Loading condition" a folder name "Global Loads Cut Planes" appears with a transverse cut inside. Open the input dialog of "transverse_Cuts", **you can create up to 50 transverse cuts** by clicking on the green circle under the table and defining the $x$-position (in $m$) of the cut, and define the $z$-position of transverse moment axis. Once your cuts sections are defined, return to the Veres dialog and click on the icon on the "Cut sections" field's right and select it.

---
Second to last option concern the **Output** files generated by Veres after running.\
When you run Veres, files are generated, but some of them are optional. You can choose to *generate strip file* (*.str*) containing the strip view of your ship, and *hydrodynamics files* containing hydrodynamic coefficients (*.re7*) and wave excitation forces (*.re8*). If you've chosen another calculation method than Strip-theory formulation (2D ordinary), two additional options are propose, *generate pressure file* (*.re6*) that contains the total dynamic pressure distribution, and *generate wamit files*.\
Most these files are used by [post processors](#post-processor) to generate results, but also by other sofwares.

---
The last option is the choice of the **Motion Coordinate System**, simply choose where you want the $z$-origin to be located, either at the COG or at the waterline.

The review of the Main tab is now finished, next in the list is the **Vessel** tab.

#### Vessel
![veres editor vessel tab](Pictures/ShipX%20view/Veres/vessel_veres.png)

The Vessel tab is composed of 3 sections, the most important you must fill is the **Mass distribution** section. It's composed of 7 fields but only *4 of them have to be filled* :
- LCG relative to AP & Mass are in read only so don't worry about them;
- *VCG* : Vertical Center of Gravity in $m$ relative to the baseline;
- *Roll radius ($r_{44}$)* : It can be calculating with the following formula : $r_{44} = \sqrt{\dfrac{I_{xx}}{displacement}}$. The typical values are between $0.3B$ and $0.45B$ where $B$ is the ship's breadth;
- *Pitch radius ($r_{55}$)* : It can be calculating with the following formula : $r_{55} = \sqrt{\dfrac{I_{yy}}{displacement}}$. The typical values are between $0.2L_{pp}$ and $0.3L_{pp}$;
- *Yaw radius ($r_{66}$)* : It can be calculating with the following formula : $r_{66} = \sqrt{\dfrac{I_{zz}}{displacement}}$. The typical values are between $0.25L_{pp}$ and $0.3L_{pp}$;
- Coupled Roll-Yaw Radius ($r_{64}$) : In general, the value is approximated to $0$.

In the second section, you have the possiblity to calculate **GM** or the **Metacentric height**, or to set the value yourself. [See here](#marin-terms-definition) for more details about GM.

Finally the **Mean dynamic position** section is

#### Motion control
![veres editor motion control tab](Pictures/ShipX%20view/Veres/motion-control_veres.png)

**Motion control** is the place where you add all the things that can influence ship's motion like bilge keel (if viscous roll damping is include), foils, moonpool, Roll Damping Tanks and Viscous Roll Damping, but also set the wave amplitude (when there are non-linear terms like in viscous roll damping).\
As you can see in the picture when you check one ShipX will ask you to select the object, so you need to create them (see [Additional feature](#additional-feature)).

#### Condition
![veres editor condition tab](Pictures/ShipX%20view/Veres/condition_veres.png)

In Condition tab you can set the **environmental conditions** of your simulation, like the **vessel velocities** (in *kn*), the **wave periods** (in *s*) and the **wave headings** (in *deg*).\
An easy way to fill the tables is clicking on "Set default condition values" in the upper left corner, then modify the values to adapt them to your simulation.

#### Mass distribution

Only available when you've enabled **Calculate global loads**, this tab is composed of one table which change depending on the mass distribution type you chose :
- **Continuous mass distribution** : The table look like the picture below. To fill it imagine your ship cut in several sections along the $x$-axis for each section you need : the **Longitudinal position** being the $x$-position of the section's center from the AP in *m*, the **VCG** from the baseline in *m*, the **ratio mass/length** in *kg/m* and the **ratio moment of inertia/length** in *kg m^2/m*.
![Mass distribution table with continuous mass distribution option](Pictures/ShipX%20view/Veres/continuous-mass-distribution.png)

- **Discrete weights** : The table look like the picture below. To fill it you need to fill the table with the **coordinates of the COG's objects** in *m* with the same origin define in the [coordinate system subsubsection](#coordinate-system), and their **mass** in *kg*. The "objects" are the items in the ship located at a specific position in the ship like engines, tanks, cargo, *etc*.
![Mass distribution table with discrete weights option](Pictures/ShipX%20view/Veres/discrete-weights.png)