class EntitiesClass:
    def __init__(self, Nr=0, Name='', geo=[], cont=[]):
        self.Nr = Nr
        self.Name = Name
        self.basep = Point(x=0.0, y=0.0)
        self.geo = geo
        self.cont = cont

    def __str__(self):
        # how to print the object
        return "\nNr:      %s" % self.Nr +\
               "\nName:    %s" % self.Name +\
               "\nBasep:   %s" % self.basep +\
               "\nNumber of Geometries: %i" % len(self.geo) +\
               "\nNumber of Contours:   %i" % len(self.cont)

    def get_insert_nr(self):
        insert_nr = 0
        for i in range(len(self.geo)):
            if "Insert" in self.geo[i].Typ:
                insert_nr += 1
        return insert_nr


layers = valuesDXF.entities.get_used_layers()