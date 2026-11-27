"""OF-02 proposed room. Metres from the south-west corner. Boxes use centre XY, base Z."""
def pieces():
    items = []
    def box(name, material, x, y, z, sx, sy, sz):
        items.append((name, material, x, y, z, sx, sy, sz))
    box("Terracotta floor","clay",2.7,1.8,-.12,5.4,3.6,.12)
    box("Insulated soffit","lime",2.7,1.8,2.70,5.55,3.75,.20)
    for x in (.18,1.44,2.70,3.96,5.22):
        box("Oak ceiling joist","oak",x,1.8,2.57,.10,3.6,.13)
    for name,x,length in (("West return",.40,.80),("East return",3.60,3.60)):
        box(name,"lime",x,3.60,0,length,.12,2.70)
    box("Sliding doorway head","lime",1.30,3.60,2.10,1,.12,.60)
    box("Fan coil","cream",3.75,3.50,2.05,.95,.20,.28)
    for side,length in (("south",5.4),("west",3.6),("east",3.6)):
        def edge(name,mat,along,height,width,depth,rise):
            if side == "south":
                box(side+" "+name,mat,along,0,height,width,depth,rise)
            else:
                box(side+" "+name,mat,0 if side=="west" else 5.4,along,height,depth,width,rise)
        bays = 4 if side=="south" else 3
        edge("plinth","lime",length/2,0,length,.15,.55)
        edge("glazing","glass",length/2,.55,length,.018,1.95)
        for level in (.55,2.07,2.5):
            edge("rail","green",length/2,level,length,.09,.065)
        for i in range(bays+1):
            edge("mullion","green",length*i/bays,.55,.07,.10,1.95)
        edge("external screen cassette","green",length/2,2.55,length,.16,.10)
    box("Oak reading table","oak",2.18,1.45,.71,1.5,.86,.07)
    for x in (1.53,2.83):
        for y in (1.13,1.77):
            box("Table leg","oak",x,y,0,.09,.09,.71)
    for x,sign in ((3.2,1),(1.14,-1)):
        box("Upholstered chair seat","umber",x,1.45,.40,.48,.52,.10)
        box("Upholstered chair back","umber",x+sign*.22,1.45,.49,.075,.52,.37)
        for dx in (-.18,.18):
            for dy in (-.20,.20):
                box("Chair foot","oak",x+dx,1.45+dy,0,.055,.055,.40)
    box("Sideboard","green",4.60,3.25,.12,1.30,.43,.70)
    box("Sideboard top","oak",4.60,3.25,.82,1.34,.47,.04)
    return items
