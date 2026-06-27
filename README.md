# Pokemon-Speedrunning-Router-and-Tracker
Program that allows one to create routes and track caught pokemon for speedrunning. It also aloows multiple people to track pokemon simultaneously using a Firebase Realtime Database.

## Setup (Database for Multi-user Connection)

1. Create a Firebase Account
2. Create a new Project (I would suggest unchecking all the optional things that google push forward)
3. On the left panel, Database & Storage -> Realtime Database
<img width="573" height="337" alt="image" src="https://github.com/user-attachments/assets/6e28b0f1-53af-4879-a68d-2ebfe7d5f594" />

4. Click "Create Database"
5. Select the nearest region to you
6. Select "Start in Locked Mode"
7. Click "Enable"
8. Copy the URL
<img width="606" height="165" alt="image" src="https://github.com/user-attachments/assets/2ab3cc57-55de-4641-91be-472f21be8b39" />

9. Go over to Setting -> Service Accounts
<img width="542" height="295" alt="image" src="https://github.com/user-attachments/assets/a9c0138d-58aa-4c99-b965-e073b42dbb6f" />

10. Click on "Generate new private key" at the bottom and download the .json file
<img width="1073" height="852" alt="image" src="https://github.com/user-attachments/assets/4a6274d9-9c66-4ecf-a6d5-a33128399521" />

11. Open the .json file and add this in the next line after the ```{```
```  "databaseURL": "<the url you copied earlier>",```
<img width="722" height="186" alt="image" src="https://github.com/user-attachments/assets/fd2f618c-99d9-46dd-be1d-c2fedbbb5a80" />

12. Save and close the file

## Setup (For Offline Mode Pokedex Tracker)

1. Download the latest release of the program and one of the pokedexes in ```/pokedexes``` in the github
2. Launch the program
3. Right Click on the left side section and click on "Open Pokedex File"
4. Select the downloaded pokedex file
5. To edit/delete a pokemon from the pokedex, middle-click on its square
6. To add a new pokemon to the pokedex, middle-click on the counter or between the scrollbar and the squares
7. To create a pokedex file from scratch, create a new empty .json file and open that file in the program
8. **IMPORTANT**: Offline Mode does not have autosave (since no live database), so if you made any changes, remember to save the pokedex file manually (Right-Click -> Save Pokedex File)

## Setup (For Online Mode Pokedex Tracker)

1. Download the latest release of the program and the pokedex file everyone is using
2. Setup the Firebase database like shown above (if your not the one who setup the database, get the key from your friend)
3. Launch the Program
4. Right-click on the left side section and click on "Open Database Credentials File"
5. Select the database key .json file
6. Now you can open then pokedex file similar to the offline mode setup
> Note: The Database can host multiple pokedexes at once. The way to determine the pokedex you're using is based on the name of the pokedex file you have loaded

## Setup (Routing Section)

1. The right-side section of the program can be used to load a custom routing file (routing files cannot be synced across players, cause why would it need to be)
2. To open a routing file, right-click the right-side section, then click "Open Routing File"
3. To edit a route section, middle-click on the section
4. To add a new route section, middle-click on the empty spaces
6. To make a new routing file, create a new .json file and load it like previously
7. **IMPORTANT**: No live database sync, so no autosave, remember to save the routing file manually (Right-Click -> Save Routing File)

> Note: For now there is no way to reorder a route in the program, you can do that by opening the .json routing file and then changing the order number of each section
