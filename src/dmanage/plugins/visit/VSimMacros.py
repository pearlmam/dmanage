def user_macro_fontUp():
    # Logging for SetAnnotationObjectOptions is not implemented yet.
    AnnotationAtts = GetAnnotationAttributes()
    AnnotationAtts.axes2D.xAxis.title.font.scale = AnnotationAtts.axes2D.xAxis.title.font.scale + 1
    AnnotationAtts.axes2D.xAxis.label.font.scale = AnnotationAtts.axes2D.xAxis.label.font.scale + 1
    AnnotationAtts.axes2D.yAxis.title.font.scale = AnnotationAtts.axes2D.yAxis.title.font.scale + 1
    AnnotationAtts.axes2D.yAxis.label.font.scale = AnnotationAtts.axes2D.yAxis.label.font.scale + 1
    AnnotationAtts.userInfoFlag = 0
    AnnotationAtts.databaseInfoFlag = 0
    SetAnnotationAttributes(AnnotationAtts)
    maxFontHeight = []
    for name in GetAnnotationObjectNames():
        vectorPlotLegend = GetAnnotationObject(name)
        maxFontHeight = maxFontHeight + [vectorPlotLegend.fontHeight]
    maxFontHeight = max(maxFontHeight)
    for name in GetAnnotationObjectNames():
        vectorPlotLegend = GetAnnotationObject(name)
        vectorPlotLegend.yScale = 1
        vectorPlotLegend.xScale = 1
        vectorPlotLegend.numberFormat = "%# -5.2g"
        vectorPlotLegend.fontHeight = maxFontHeight + .01
        vectorPlotLegend.fontBold = 1
        # vectorPlotLegend.useCustomTitle = 1
        # vectorPlotLegend.customTitle = "Electric Field (V/m)"

RegisterMacro("fontUp", user_macro_fontUp)


def user_macro_fontDown():
    # Logging for SetAnnotationObjectOptions is not implemented yet.
    AnnotationAtts = GetAnnotationAttributes()
    AnnotationAtts.axes2D.xAxis.title.font.scale = AnnotationAtts.axes2D.xAxis.title.font.scale - 1
    AnnotationAtts.axes2D.xAxis.label.font.scale = AnnotationAtts.axes2D.xAxis.label.font.scale - 1
    AnnotationAtts.axes2D.yAxis.title.font.scale = AnnotationAtts.axes2D.yAxis.title.font.scale - 1
    AnnotationAtts.axes2D.yAxis.label.font.scale = AnnotationAtts.axes2D.yAxis.label.font.scale - 1
    AnnotationAtts.userInfoFlag = 0
    AnnotationAtts.databaseInfoFlag = 0
    SetAnnotationAttributes(AnnotationAtts)
    
    for name in GetAnnotationObjectNames():
        vectorPlotLegend = GetAnnotationObject(name)
        vectorPlotLegend.yScale = 1
        vectorPlotLegend.xScale = 1
        vectorPlotLegend.numberFormat = "%# -5.2g"
        vectorPlotLegend.fontHeight = vectorPlotLegend.fontHeight - .01
        vectorPlotLegend.fontBold = 1
        # vectorPlotLegend.useCustomTitle = 1
        # vectorPlotLegend.customTitle = "Electric Field (V/m)"

RegisterMacro("fontDown", user_macro_fontDown)

def user_macro_loadHist():
    import glob
    histFile = glob.glob( './*_History.h5')[0]
    histDatabase = "localhost:"+histFile
    OpenDatabase(histDatabase, 0)
RegisterMacro("loadHist", user_macro_loadHist)

def user_macro_movAvg():
    pL = GetPlotList()
    Es = Expressions()
    Navg = 0
    for E in Es:
        #print(E[0])
        if E[0] == 'Navg':
            Navg = int(E[1])
    if Navg < 1:
        Navg = 10
        DefineScalarExpression("Navg",'%s'%Navg)
        
    for i in range(pL.GetNumPlots()):
        name = pL.GetPlots(i).plotVar
        if not 'Avg' in name:
            
            newName = name+'Avg%i'%Navg
            print(newName)
            DefineCurveExpression(newName, "mean_filter(%s,%i)"%(name,Navg))  # cant put 'Navg' here because it converts to float anf mean_filter() needs int
            SetActivePlots((i))
            ChangeActivePlotsVar(newName)
        else:
            baseName = name.split('Avg')[0]
            newName = baseName+'Avg%i'%Navg
            DefineCurveExpression(newName, "mean_filter(%s,%i)"%(baseName,Navg))  # cant put 'Navg' here because it converts to float anf mean_filter() needs int
            DeleteExpression(name)
            SetActivePlots((i))
            ChangeActivePlotsVar(newName)

RegisterMacro("movAvg", user_macro_movAvg)

def user_macro_plotParticle():
    WI = GetWindowInformation()
    md = GetMetaData(WI.activeSource)
    
    # print(md)
    for i in range(md.GetNumScalars()):
        varName = md.GetScalars(i).name
        print(varName)
        if ('_x' in varName) or (varName == 'x'):
            xVar = varName
        elif ('_y' in varName) or (varName == 'y'):
            yVar = varName
        elif ('_z' in varName) or (varName == 'z' and 'xVar' not in vars()):
            xVar = varName
        elif ('_r' in varName) or (varName == 'r'):
            yVar = varName
            
    ScatterAtts = ScatterAttributes()
    ScatterAtts.var1 = xVar
    ScatterAtts.var1Role = ScatterAtts.Coordinate0  # Coordinate0, Coordinate1, Coordinate2, Color, NONE
    ScatterAtts.var2Role = ScatterAtts.Coordinate1  # Coordinate0, Coordinate1, Coordinate2, Color, NONE
    ScatterAtts.var2 = yVar
    ScatterAtts.scaleCube = 0
    ScatterAtts.colorType = ScatterAtts.ColorBySingleColor  # ColorByForegroundColor, ColorBySingleColor, ColorByColorTable
    ScatterAtts.singleColor = (0, 0, 255, 255)
    ScatterAtts.legendFlag = 0
    SetDefaultPlotOptions(ScatterAtts)
    AddPlot("Scatter", xVar, 1, 0)
    slider = CreateAnnotationObject("TimeSlider")
    slider.height = 0.07
    slider.position = (.2, .01)
    slider.width = 0.6
    SuppressMessages(1)
    DrawPlots()
    AnnotationAtts = AnnotationAttributes()
    AnnotationAtts.userInfoFlag = 0
    AnnotationAtts.databaseInfoFlag = 0
    SetAnnotationAttributes(AnnotationAtts)
RegisterMacro("plotParticle", user_macro_plotParticle)

def user_macro_plotGeo():

    AddPlot("Subset", "domains(poly)", 1, 0)
    SubsetAtts = SubsetAttributes()
    SubsetAtts.colorType = SubsetAtts.ColorBySingleColor  # ColorBySingleColor, ColorByMultipleColors, ColorByColorTable
    SubsetAtts.legendFlag = 0
    SubsetAtts.lineWidth = 2
    SubsetAtts.singleColor = (0, 0, 0, 255)
    SubsetAtts.wireframe = 0
    SetPlotOptions(SubsetAtts)
    WI = GetWindowInformation()
    md = GetMetaData(WI.activeSource)
    if md.GetMeshes(0).spatialDimension == 3:
      AddOperator("Slice", 0)
      SliceAtts = SliceAttributes()
      SliceAtts.originType = SliceAtts.Intercept  # Point, Intercept, Percent, Zone, Node
      SliceAtts.originIntercept = 0
      SliceAtts.originPercent = 0
      SliceAtts.normal = (0, 0, 1)
      SliceAtts.axisType = SliceAtts.ZAxis  # XAxis, YAxis, ZAxis, Arbitrary, ThetaPhi
      SliceAtts.upAxis = (0, 1, 0)
      SliceAtts.project2d = 1
      SliceAtts.interactive = 1
      #SliceAtts.meshName = "compGridGlobal"
      SliceAtts.theta = 0
      SliceAtts.phi = 90
      SetOperatorOptions(SliceAtts, 0, 1)

    # it can be either "compGridGlobal" or "globalGridGlobal"
    meshName = md.GetMeshes(0).name
    print(meshName)
    AddPlot("Mesh", meshName, 1, 0)
    MeshAtts = MeshAttributes()
    MeshAtts.legendFlag = 0
    MeshAtts.opacity = 0.25
    SetPlotOptions(MeshAtts)

    if md.GetMeshes(0).spatialDimension == 3:
      AddOperator("Slice", 0)
      SliceAtts = SliceAttributes()
      SliceAtts.originType = SliceAtts.Intercept  # Point, Intercept, Percent, Zone, Node
      SliceAtts.originIntercept = 0
      SliceAtts.originPercent = 0
      SliceAtts.normal = (0, 0, 1)
      SliceAtts.axisType = SliceAtts.ZAxis  # XAxis, YAxis, ZAxis, Arbitrary, ThetaPhi
      SliceAtts.upAxis = (0, 1, 0)
      SliceAtts.project2d = 1
      SliceAtts.interactive = 1
      #SliceAtts.meshName = "compGridGlobal"
      SliceAtts.theta = 0
      SliceAtts.phi = 90
      SetOperatorOptions(SliceAtts, 0, 1)
    DrawPlots()

    AnnotationAtts = AnnotationAttributes()
    AnnotationAtts.userInfoFlag = 0
    AnnotationAtts.databaseInfoFlag = 0
    SetAnnotationAttributes(AnnotationAtts)
RegisterMacro("plotGeo", user_macro_plotGeo)



def user_macro_reload():
    import glob
    g = GetGlobalAttributes()
    #print(g)
    activeWindow = g.activeWindow+1
    print('####   Checking Timer States   ####')
    correlations = {}
    for window in g.windows:
        SetActiveWindow(window)
        pL = GetPlotList()
        timeSliders = GetTimeSliders()
        activeTimeSlider=GetActiveTimeSlider()
        correlationSliders = []
        correlationName=None
        for timeSlider in timeSliders:
            if not 'Correlation' in timeSlider:
                correlationSliders = correlationSliders + [timeSlider]
            else:
                updateCorrelation = True
                correlationName = timeSlider
        if not correlationName is None:
            correlations[correlationName] = correlationSliders
        
        for source in g.sources:
            for timeSlider in timeSliders:
                if ((timeSlider == source) or ('Correlation' in timeSlider)) and (source in timeSliders):
                    
                    print('active window %i: %s found'%(window,timeSlider))
                    SetActiveTimeSlider(timeSlider)
                    sourceString = source.replace('localhost:','').replace(' database','')
                    #print(sourceString)
                    lastState = len(glob.glob(sourceString))-1
                    plotState = TimeSliderGetNStates() - 1
                    #print('lastState: %i'%lastState)
                    #print('plotState: %i'%plotState)
                    if plotState > lastState:
                        print('  setting time state to %i'%lastState)
                        SetTimeSliderState(lastState)
        if not activeTimeSlider == '':
            SetActiveTimeSlider(activeTimeSlider) # need to reset active timeSlider on last open window
    print('####   Reopening Databases   ####')
    for source in g.sources:
        ReOpenDatabase(source)
        if not activeTimeSlider == '':
            SetActiveTimeSlider(activeTimeSlider) # need to reset active timeSlider on last open window
    
    print('####   updating Correlations   ####')
    for name,dbs in correlations.items():
        print("Updating '%s' with databases:%s"%(correlationName,correlationSliders))
        AlterDatabaseCorrelation(name,dbs,0)
    SetActiveWindow(activeWindow) 
    # CheckForNewStates()
RegisterMacro("reload", user_macro_reload)




