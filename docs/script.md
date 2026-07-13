### talking head intro

[outdoors] hi! I decided it would be a wonderful idea to design, manufacture, and assemble a combat robot to take to open sauce.

Sounds like a great idea! There is just one teeny tiny little problem with this plan though. It’s currently the 29th [show calendar] and I only have 20 days to design, manufacture, and build it before I have to be at opensauce. To make this even more exciting [strike out a week] I’m gone on a mission trip for 7 of those days.

### montage with narration

[montage] [research on chair] I had already been doing the research on combat robotics for the past week or so and had decided that I wanted to build a meltybrain. What is a meltybrain? [cut to orbitting early version of cad] Basically a spinning roomba of death with two steel spikes on the sides. [cut to project liftoff] Project Liftoff is one of the most famous meltys designed by the Kazmer family to compete in NHRL. Meltys tend to be incredibly robust and extremely deadly when driven correctly but their downside is extremely high stress on their electronics and complicated firmware.

### mathy part of the video

[cut to motion canvas] [beat 1: meltyspin up with arrow] Because meltys spin so fast they don’t have a constant forward direction. [beat 2: kick animation] In order to drift across the floor they have to “kick“ the motors at a specific point in each rotation to nudge it in a direction. Given a robot spinning at 3k rpm that is about 50 kicks a second which can give you some decent speed.

[beat 3: gyro redline] Most commerically available gyros aren’t able to handle such rotational speeds and cap out at a few thousand degrees per second at most or less than 4-500 rpm so we have to use accelerometers. [beat 4: accelerometer math scene] An acceleremeter is able to measure rotation by sensing the pull toward the outside of the bot. The faster you spin the bot the harder the pull is. If you have ever spun a ball on a string this is very similar. This acceleration [show a = ω² r] can be expressed as the spin rate squared times the distance from the center. We can flip the equation to solve for ω [show rearrange ω² =  a/r and then morph into ω = √(a / r)] and since we know the radius of the accelerometer and we know the acceleration we have solved for rotation rate. Unfortunately because rotation is quadratically related to acceleration it means that the g forces the accelerometer experiences grow drastically with increased rpm [rpm from 0 to 4500 mapped to g force reading at 20mm graph animate growing]. This means that at high speeds everything is perfect. We have extremely high signal and low noise but at lower speeds we have insanely high noise and next to no signal. 

[show integration graph of heading over time replacing bot spinning] Rotation rate is not quite what we need to precisely control the motors however. We need heading which can be integrated from rotation rate [show final equation theta = integrate(w dt) ideally animated in the same way as before]

[go back to spinng robot and start showing error; equations can clear] Because we integrate the rotation rate over time any little errors in our measurement also add up over time leading to heading drift. Now what i’ve been explaining so far is technically correct but a major simplification. The single accelerometer doesn’t just detect the pull toward the outside of the bot but it [show readout graph spiking widly] detects every bump in the floor, every hit, and every translation and can’t tell any of them apart. [add 3 acceleremeter dots with 2 at 18mm and 1 at 12mm at 0, 90, and 210 degrees] Now this is the fancy part of my bot. [show shove: show two line sensor read out with shove] If the robot gets shoved all 3 sensors feel that shove with the same magnitude but the spin pull varies by location. [animation subtraction between inner and outer sensor and show pure graph] If we subtract one sensor’s reading from another we can cancel out the shove. If we add a third sensor at another angle we can tell from which direction the shove came from.

Now because we have 6 measurements and 4 unknowns [show each gyro x and y measurement and a gap and then spin rate squared, angular acceleration, linear acceleration x and y] we can start to verify our work across sensors. We use a Kalman filter to predict where the robot should be next tick and then compare the sensor readings to that prediction.

[hide equations; show ekf approximation bell curves honing in on true answer] All of them will always be slightly wrong but they will usually be wrong in different ways. By weighting each measurement based on how much we trust the source at each moment we can fuse together our sources. The weight of each source becomes the width of a bell curve and then we can pick the highests point added between all of our curves to be our new prediction. We can even add extra sources like eRPM or (at lower speeds) a gyro to improve our accuracy. [ekf bell curves having finished multiple cycles hone in on final sensor measurement]

### Buillllllld

[scroll each datasheet] The PCB is designed around 3 accelerometers: 2 of the high-g H3LIS331DLTR from STM mounted at the outer radius and the inner LSM6DSV320XTR dual accelerometer / gyro also from STM. The MCU is an rp2350 on a xiao board chosen because of its PIO for DSHOT and also mostly just because I like working with RP chips and their ecosystem.

[cut to shot of kicad] The board is a 4 layer stackup with 2 outer signal layers and a power and ground inner layer. [power layer] The power layer is split into [highlight each with mouse] a VBUS, 5V, and 3V3 sections while the ground layer was kept completely clear to provide a clean groundplane for the traces above.

[go to schematic] The schematic is divided into a few subsheets. We have the power sheet with a selectable battery voltage cutoff level and the buck coverter. The IMU array sheet with the 3 accelerometers and their chip select shift register to help save on GPIO pins. Finally we have the status led sheet with our top and bottom RGB leds and our top and bottom heading leds.

[onshape assembly] Moving over to CAD we have the fully assembled bot here with the motors, wheels, pcb, and battery. I've used onshape for pretty much all of my cad projects (of which this was by far the biggest and taught me the most) and its great most of the time but I do wish it worked offline as it was a strugle to work on this in low internet environments.

[move to google sheets] My parts list is fairly long with most of the cost eaten by the PCB. Turns out double sided assembly and rush shipping are crazy expensive. The shipping is going to be crazy close and hopefully it will arrive in time for opensauce.

The only thing left to do now is build it!

### Assembly TBD
