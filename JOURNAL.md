# The great journey of the one and only Holy Guacamole 🥑

**Running hour counter:** 83h

Okay this is a wee bit out of order bc I didn't start writing all of this down into after I realized I could do this for Outpost but from screenshots and git time stamps and my memory this is the best recontruction of the process up till now.

### Day numero uno: Saturday June 20th [5h15m]

I saw this [amazing video](https://www.youtube.com/watch?v=c7CI6yBTKMc) by Maker's Muse about a technique in orcaslicer to print stronger solid prints and then got fascinated by antweight combat robotics. I ended up going down a whole rabbit hole for the rest of the day. I discovered ring spinners pretty quickly (huge spinning blade around the outside) which seemed fascinating but a ton of work to build (some people have even made their [own motors](https://www.youtube.com/watch?v=scGufLuW8Do)). I also discovered that there was a competition ([Buckeye Bash](https://www.robotcombatevents.com/events/7385)) less then 45 minutes from me that was happening in August.

I was originally planning to do a plastic ant since it seemed quite cheap but as I started doing more research and looked at the rules for the competition it seemed more resonable just to do a full antweight robot. The [MCRA ruleset](https://docs.google.com/document/d/1A3H4qUD5gavUpnrbM_T5pSLp5FmKuVVwXHL0bRRfBec/edit?tab=t.0#heading=h.q0ajfns46f7y) is quite fascinating to read through and has such sections such as "10.4 Weapons with an open flame are not allowed. 10.4.2 Explosives or flammable solids such as: 10.4.2.2 Military Explosives, etc." which is absolutely hilarious and does make me wonder if anyone has tried to do that before.

One of the main things I was really curious about was something I could do a ton of software stuff with. I'm okayish at hardware but looooooove software and really wanted to design something that could leverage that. I remembered that the Hacksmith had done a bunch of work with autonymous operation at the large 30lb level but it mostly relied on computer vision outside the cage which seemed finicky and unreliable to me especially for smaller events where the cages are all different.

In the course of doing research about what the current software layout is I found out about meltys. Now meltys are conceptually very simple. You take the whole bot and you strap some metal blades to the outside and you have a hockey puck of death. Since you are able to rotate the entire robot directly and convert it into kinetic energy you are able use the whole robot. Thats 70% more robot in every shot! Cave Johnson aside its a pretty insane robot archtype that is also very uncommon. Hardware wise its very simple. Just add one or two motors and spin them opposite directions spinning your bot up to high rpms of about 2-4k. The hard part is the software. You essentially have to pulse the motors at very specific timings in the rotation in order to get it to translate across the floor. This is annoyingly hard to do because you need to know the rotation speed so you can also keep a heading lock. Most gyros cap out at much much lower rpms so most people end up going with an accelerometer. Even with an accelerometer though you have problems with g forces because at rpms like this you can easily experience 400-500 gs even just 3 cm from the center.

Now that I know I absolutely had to build a meltybrain I started looking at the hardware requirements. Keep in mind I didn't quite realize the IMU challenge quite yet and I was absolutely flying high on the front end of the Dunning-Kruger curve. I figured that a N20 gear motor would probably be fine right??? But then as I started doing more research I discovered it would not in fact be fine. The original opensource melty code [openmelt](https://github.com/nothinglabs/openmelt2/) used a big brushless motor and some of the newer ones like [potato melt](https://github.com/skysdottir/PotatoMelt) use brushless motors which means I need an esc :(

I knew I probably wanted to use an rp2350 for the board since they are just really nice to build with and their software stack is lovely. Finding an imu took ages especially since there are very few proper writeups about meltys on the public internet. But I basically stayed in this research hole getting more and more confused and rapidly feeling the complexity rise for the rest of the night. I went to bed at 23:45 that night having worked on this entirely since dinner at around 18:30ish.

### Day 2: June 21st [4h]

I started writing up a doc and a [google sheet](https://docs.google.com/spreadsheets/d/1paAJ0Wakvn5M726pM15FUGLVGKdC47_Wt41PN1yA9PQ/edit?gid=0#gid=0) of the things I was going to need for this and quickly realized it was going to be a ton of stuff. My goal from the start was to keep everything sub $250 though which did seem doable. I did some research and from what I could find PLA+ seemed to be a fairly well recommended choice for antweight bots in general and my local microcenter had some pretty green filament which looked nice.

I also ended up changing the name from Bogey One to Holy Guacamole once I saw the green filament as it kinda just fit perfectly. I also started looking for specific IMUs and nailed down the motors I wanted to get to the [Palm Beach Bots D2822](https://palmbeachbots.com/products/palm-beach-bots-d2822-brushless-outrunner-1100kv-0-125in-shaft) motors as they had a low enough kv that they could spin at a "low" rpm of 2-4k rpm. Finding a lower kv high torque motor was actually suprisingly hard especially since I was coming from the drone world so thats where I looked first and those are the exact opposite type of motor especially in this size range.

### Day 3: June 22nd [2.5h]

I finally made it to microcenter and bought the filament. I had to drag out my A1 mini from the closet and shockingly it still worked great! I printed a test cube and it was amazingly solid. It felt almost like an injection molded part which was crazy.

![microcenter](https://cdn.hackclub.com/019f29b7-a0f5-732b-a3a4-d7af0a59c670/image.png)

I also was able to finalize where I wanted to buy my main parts from and find links for everything

![google sheets](https://cdn.hackclub.com/019f29b9-d372-7dd4-8a48-a7b5d472382d/image.png)

### Day 4: June 23rd [3h]

I started the cad and got an okayish looking round hockey puck thing but then wasn't entirely sure what to do next so I ended up emailing Palm Beach Bots and they actually had cad models for almost all of the parts I was planning on using! I started working on making holes for the motors to sit in and started also experimenting with parametric variables but I very much didn't know what I was doing and also got sucked down a rabbit hole of trying to reverse engineer the bambu lab network plugin (absolute hell btw) to get it to work with OrcaSlicer.

### Day 5: June 24th [5h]

I started fleshing out the pcb design! I realized that my inital ideas about how to do the gyro were a bit flawed and started reading a few research papers about using just accelerometers to measure rotation reliably. I ended up coming up with a really interesting approach that uses 3 accelerometers arranged in a triangle shape with one of them a bit closer to the center. This arrangement was inspired by a [paper](https://arxiv.org/abs/2108.09834
) on arxiv and theoretically should help be able to discriminate better between changes in different axis as well as elimentating deadzones. I settled on the [H3LIS331DL](https://www.st.com/resource/en/datasheet/h3lis331dl.pdf) from ST which is able to withstand up to 400gs and placed it at 20mm from the center which should keep it at about 350gs at max rpm.

I also realized I had a bit of a GPIO problem and needed an expander eventually settling on the [MCP23S17](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf) spi expander to help manage the CS pins on the accelerometers. I was able to get a fair bit of the schematic done before the day was done which I was fairly happy with.

### Day 6-8: June 25-27th - the amazing breakthrough [9h]

At this point I was kind of limping along with what i could glean from the internet and it was kind of a struggle to get more info on meltys. My friend Adam found out that I was looking to build a melty and invited me to the Hockey Pucks Of D̰͆͝E͕͆ͅA̤ͭ̂TͮͫH̞̃̎ discord server. This was the best thing that ever happened to this project. There are some absolutely incredible humans on there who have been working on meltys for the past 5 or more years and know so incredibly much. I started reading through as much of the discord as I could but there was just so much information available it was hard to stop lol.

![the sad sad cad](https://cdn.hackclub.com/019f29d1-1308-7b24-981f-47f7932ec5d0/image.png)

I made a project channel in the discord and also started working on the cad a bit more. At this point its still in a pretty sorry state and I was still feeling very intimidated by onshape. It certainly didn't help that I was using my mac still so a touchpad for cad was miserable. I worked on the pcb a bunch more but that was about it for the day. I was able to get some motor cut outs working though and got into some interesting conversations about motors on the discord.

![eod cad](https://cdn.hackclub.com/019f29d3-dd82-7696-a432-730e246332e5/image.png)

I also did a bunch of research into wheels and found that foam wheels with a conformal coating and then silicone seem to be pretty highly recommended as having great traction and durability

### Day 9: June 28th [5h]

I actually got some good cad working!!!!!

![good cad!!!](https://cdn.hackclub.com/019f29d6-0a03-71b6-9ce8-8569189f35be/image.png)

I had switched to my pcb at this point and ended up spending about 5 hours getting to this point and was feeling actually amazingly confident with onshape!

I also had gotten the schematic mostly to a place where I liked to and gotten it semi organized. At this point I asked for a design review in both slack and discord and got some great feedback!

![schematic round 1](https://cdn.hackclub.com/019f29d8-8dcf-7c57-9735-a8f8f4cb50d5/image.png)

### Day 10: June 29th [4.5h]

![nice schematic](https://cdn.hackclub.com/019f29d9-f9b8-7135-a23b-37a2ee21226e/image.png)

The schematic being so messy really stinking bugged me so I spent far too long organizing it into hierarchical sheets and integrating the feedback I got on the first version. I also cleaned up a bunch of the messy wiring that just didn't look very nice.

I also printed the first iteration of the CAD at this point to see if it fit the newly arrived motors and esc. I printed it in crazy low infill but everything did mostly fit which was amazing for my confidence. At this point I also started considering outpost as something that might make sense for this project and that kicked my brain into high gear and I ended up spending another several hours refining the cad again and redesigned the way the top and bottom fit together and got screws all fancy and working.

![printed model](https://cdn.hackclub.com/019f29db-d08c-7887-9f49-3c05a1e6ce42/image.png)

### Day 11: June 30th [3.5h]

I spent a bit researching screw types which are more complicated then I realized and then ended up redoing to the cad again to switch to partially sunk machine screws instead of the fully countersunk screws I was attempting to put in the cad before.

![fancy screws](https://cdn.hackclub.com/019f29df-d8ab-7d07-bf5e-53f3f810fd46/image.png)

I also spent a while double checking my BOM and making sure I had all the things I was going to need. Ended up staying up way too late thinking about melties and the ways I could optimize mine.

### Days 12 and 13: July 1st and 2nd [0h]

I did pretty much nothing these two days because I flew to NYC to spend 2 days onsite with [Charm](https://charm.land/). It was a ton of fun to meet everyone IRL and I got to visit the slack office in salesforce tower! I also was able to play with my new camera a bunch and took a bunch of great photos :)

![photo of me and my host Ale in salesforce tower](https://cdn.hackclub.com/019f29e3-6dcf-7037-9df0-f1211e137724/image.png)
![some photos I took](https://cdn.hackclub.com/019f29e4-2a8a-7881-ae03-399f2ea9c33f/image.png)

### Day 14: June 3rd [8h]

[15:00ish] This brings me to the present where I'm writing this and just finished a final review of my schematic. It took actually a shockingly long time I write this all out (about 2 hours 😭) but it was really fun to recap and kind of insane to realize that this entire project came together in 2 weeks. I'm going on a mission trip tomorrow so I have to finish routing the pcb tonight and get it sent off for one final design review from a real EE (i'm so thankful for this) and then get it made at JLC! I'm really hoping that I can get everything made quickly enough bc outpost and opensauce are coming up wayyyy too quickly (18th and 19th for opensauce) and I have practically no time left.

[23:30] I stayed up far too late to get the pcb finished (skipped the review and will have them check the pcb hopefully quickly ish). I'm not really happy with the shape but I already had to reroute it several times so i'm not partiularly excited to do it again. I decided to see how good freerouting has gotten and its still miserable. I had to delete everything it produced as it skipped the simplest of traces. Who knows the mind of the autorouter :shrug:

![image of the horrible first pass](https://cdn.hackclub.com/019f32b5-e843-7ce7-9056-54ea9275701f/image.png)

I was able to discover a pretty good trick for designing the pcb though. If you export a top down view of the onshape model and then clean it up in an svg editor you can import it as a user drawing layer into kicad and then size your edgecuts relative to that. You do need to calibrate the scale via a reference line though.

### Day 15: June 4th (14 days to opensauce) [5h]

It's the 4th of July and i'm on the road. Started driving down to north carolina about 9 and ended up completely ripping out the entire pcb and redesigning the edgecuts so its a bit more compact. Originally started out with a 2 layer board but was having problems keeping the ground plane clean for the spi traces and was also having some problems reaching all of the components. I got inspired by someone in the melty discord to add these little protrusions off the side for screw holes.

After moving to a 4 layer design I decided on a signal-power-gnd-signal stackup splitting the power plane into 3 seconds for vbus, 3.3v, and 5v. Happily the components almost perfectly split across these lines so I only needed two traces on the powerplane. Also added a bunch of stiching vias to tie the gnd planes together and added a copper pour on the top and bottom of the board.

I'm really hoping that that i've covered everything here. I'm 90% sure I have and I've done a million reviews of the schematic and tripple checked everything. I just need to get the BOM for jlc ready which mostly just means picking caps and resisters and then get this producing. It's going to be a crazy tight turnaround as even with fast shipping JLC takes about 8 days to get to the US. I'm really hoping to have everything arrive in time.

| | |
|---|---|
| ![render 4](https://cdn.hackclub.com/019f3009-b824-7d76-9c00-3245f6e4a3f1/image.png) | ![render 3](https://cdn.hackclub.com/019f3009-b593-7781-90cb-2fa0930e5c0d/image.png) |
| ![render 2](https://cdn.hackclub.com/019f3009-b2b2-7b43-a9a8-2a6c71dd9c52/image.png) | ![render 1](https://cdn.hackclub.com/019f3009-afdf-76ce-bdc6-43f065732723/image.png) |

### Day 16: June 5th [4h]

I added some stiching vias as mpk recommended on slack and got proper copper pours on top and bottom. Started working on getting all of the bom parts ready for JLC and discovered a bug with my original SPI idea where the H3LIS331DLTR used the CS pin to enable and disable SPI is slightly broken as for some (in my dumb opionion insane but probably perfectly reasonable) reason when CS is 0 it switches to I2C instead of SPI. If I use mode 0 SPI and add a 100k pulldown to gnd on spi sck i think it should be fine. The pcb is unfortunately scarrily expensive with shipping and assembly and came out to just over $350.

![jlc quote](https://cdn.hackclub.com/019f35e9-6036-7d13-8a65-e36cf99e916d/image.png)

Also started working on the firmware and I got some good benchtest code ready and am working on the EKF fusing code. Ideally I can get a sim ready soon but that seems unlikely to get done this week (saying that i'll stay up till 4am tmrw and finish wont I :pf:).

### Day 17: June 6th [5h]

Well my prediction from yesterday was correct lol. I now have a simulator albiate a not crazy good one but it will improve. I need to do quite a lot of hardware in the loop testing before hand to iron out the bugs before I get the actual hardware. The lovely thing is that this is all pretty simple physics and so not terribly hard to model in software. I'm doing an end to end simulation running the exact same code as on the bot just with a simulation mock for the receiver, escs, and imus.

I also did a bunch of iteration on the blades as I wasn't super happy with the way that I got them initally. I tweaked them a ton but eventually had to go to sleep after messing up one of the sides and realizing I was far too tired to do good work.

![the first blades](https://cdn.hackclub.com/019f4026-944c-7564-996c-43692119e6d3/image.png)

### Day 18: June 7th [5h]

I did a bunch more work on the firmware and now have full ekf working and the sim mostly behaving! I also received my design review from solderable's EE Tyler (thank you ^^) and discovered that I put my caps too far away from the buck covertor and the imu. Thankfully it wasn't a terrible fix but I also discovered a few other issues in the process. I got a quote back from pcbway as well and they are offering $280ish which is better than jlc's $360. The main downside is that pcbway moves a wee bit slower in my experience but the quality is usually really good.

I also redesigned the toothies (my offical name for them) to be wayyyy smaller and far more lightweight than last night. They should weight about 40g each now and hopefully be a bit stronger since they don't have massive parallograms in the middle anymore.

I stayed up far too late working on this yet again and now i'm typing this up as I wait to see if i heard back from pcbway quickly and can get my design into motion. I also probably need to add a low battery cutoff to the buck convertor but thats annoying and may have to wait depending on how long everything takes and how fast pcbway gets back.

### Day 19: June 8th [6h]

I have now offically purchased the pcb! I found out a pretty big issue with the pcb initally where it extended into the wheel wells which would have prevented the wheels from turning. I extended the pcb and that also opened up some silkscreen room which is amazing. I also made a copper heatsink for the esc and tweaked the assembly model a ton to get the pcb properly mounted.

I purchased the pcb and toothies which was immensely painful. JLC ended up being $524.56 which feels insane. Tarifs / Duties alone was $115 😭

Send Cut Send was amazingly quick and also nicely cheap. The toothies cost about $4 each which wasn't bad and the copper heatsink was $7ish. Shipping was double the cost of parts hilariously. I definely want to order stuff from them again. Unfortunately the estimated shipping arrival dates on both JLC and SCS is the 16-17th right before I have to leave. It's going to be scarily close. I'm going to work a ton on the simulator and hopefully also make the wheels and assemble pretty much everything else accept for the electronics. My main worry is that it is going to be too hard to add the strain relief connections since that is liquid latex which won't transfer well on the plane. If worst comes to worst I can just solder the connections after I get there and take a small bottle of latex. We shall see.

I'm also still shocked at how much time I keep etching out of the day for this. TBF I stayed up till 3am this morning and have been spending 2 hours before and after dinner each afternoon so it does really add up.

![the pcb after extension](https://cdn.hackclub.com/019f449f-434b-725f-80b1-6ce91843d4cf/image.png)

### Day 20: June 9th [15m]

Wasn't able to do much today just confirmed the replacement of my inductor bc I grabbed the wrong lcsc part # :facepalm: Thankfully JLC was nice about it and I could just replace the part with one that fit the correct footprint. Tried to do some onshape stuff and submit the outpost forms but slow internet made that extremely painful.

### Day 21: June 10th [3h]

Today was mostly spent in the car so i worked on the firmware and got it reflecting the real world sensors much more closely. The physics model in the sim is now much more accurate and rebounds work correctly. Also was able to fix several things with the accelerometer code that was manifesting in the sim! I'm hoping that the sim will help catch all / most of the bugs if possible but who knows. I'm really hoping that the wrong part # didn't delay JLC too too long.

### Day 22: June 11th [5h]

Today was mostly a ton of work on the explainer video in motion canvas. I got the video and script most of the way to where I wanted it and also started some editing in davinci after filming the intro sequences. Recorded the voiceovers and worked on the script for absolutely ages.

![motion canvas](https://cdn.hackclub.com/019f590a-be14-717e-9a3a-1c10f228226e/image.png)

### Day 23: June 12th [10h]

Worked on finishing out the voiceovers for the first few hours and then finished editing the explainer bit of the video and started working on refining the last bits of the mounting cad. Was able to finish that and start printing the body of the bot after agonizing on how to cut down on weight in the slicer. I also was able to figure out a way to possibly get the pcb in time. I'm going to order the pcb from oshpark and get a stencil from oshcut and then assemble the parts myself. Hopefully it will be a tiny bit faster and everything should arrive in time.
