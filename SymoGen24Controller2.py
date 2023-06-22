import json
import configparser
from datetime import datetime, timedelta
import pytz
import requests
import SymoGen24Connector
from ping3 import ping
from sys import argv

def loadConfig(conf_file):
        config = configparser.ConfigParser()
        try:
                config.read_file(open('config.ini'))
                config.read(conf_file)
        except:
                exit()
        return config

def loadWeatherData(config):
        data = None
        try:
            with open(config['env']['filePathWeatherData']) as json_file:
                data = json.load(json_file)
        except:
                print('Wetterdatei fehlt oder ist fehlerhaft, bitte erst Wetterdaten neu laden!!')
                exit()
        return data

def loadPVReservierung(config):
        reservierungdata = None
        try:
            with open(config['Reservierung']['PV_ReservieungsDatei']) as json_file:
                reservierungdata = json.load(json_file)
        except:
                print('Reservieungsdatei fehlt, bitte erzeugen oder Reservierung abschalten !!')
                exit()
        return reservierungdata

def getPrognose(Stunde):
        if data['result']['watts'].get(Stunde):
            data_tmp = data['result']['watts'][Stunde]
            # Wenn Reservierung eingeschaltet und Reservierungswert vorhanden von Prognose abziehen.
            if ( PV_Reservierung_steuern == 1 and reservierungdata.get(Stunde)):
                data_tmp = data['result']['watts'][Stunde] - reservierungdata[Stunde]
                # Minuswerte verhindern
                if ( data_tmp< 0): data_tmp = 0
            getPrognose = data_tmp
        else:
            getPrognose = 0
        return getPrognose


def getRestTagesPrognoseUeberschuss( AbzugWatt, aktuelleEinspeisung, aktuellePVProduktion ):

        # alle Prognodewerte zwischen aktueller Stunde und 22:00 lesen
        format_Tag = "%Y-%m-%d"
        # aktuelle Stunde und aktuelle Minute
        Akt_Std = int(datetime.strftime(now, "%H"))
        Akt_Minute = int(datetime.strftime(now, "%M"))
        i = Akt_Std
        Pro_Uebersch_Tag = 0
        Pro_Ertrag_Tag = 0
        Pro_LadeKapa_Rest = 0
        Pro_Spitze = 0
        Grundlast_Sum = 0


        while i < BattVollUm:
            Std = datetime.strftime(now, format_Tag)+" "+ str('%0.2d' %(i)) +":00:00"
            Prognose = getPrognose(Std)

            # AKTUELL AUS
            # Stundendaempung rechnen  mit BatSparFaktor
            #tmp_Stundendaempfung = (BattVollUm - i) * BatSparFaktor
            #if tmp_Stundendaempfung < 1:
            #    tmp_Stundendaempfung = 1
            #Pro_Uebersch = (Prognose - AbzugWatt) * tmp_Stundendaempfung
            # AKTUELL AUS evtl nicht nötig

            Pro_Uebersch = (Prognose - AbzugWatt)

            # Prognosenspitzenwert für Resttag ermitteln
            if Prognose > Pro_Spitze:
                Pro_Spitze = Prognose

            # wenn nicht zur vollen Stunde, Wert anteilsmaessig
            Grundlast_tmp = Grundlast
            if i == Akt_Std:
                Prognose = (Prognose / 60 * (60 - Akt_Minute))
                Pro_Uebersch = (Pro_Uebersch / 60 * (60 - Akt_Minute))
                Grundlast_tmp = int((Grundlast / 60 * (60 - Akt_Minute)))

            Pro_Ertrag_Tag += Prognose

            if Prognose > 0:
                Grundlast_Sum += Grundlast_tmp

            if Pro_Uebersch > MaxLadung:
                Pro_Uebersch = MaxLadung

            if Pro_Uebersch > 0:
                Pro_Uebersch_Tag += Pro_Uebersch
            else:
                Pro_Uebersch = 0

            # Ab hier Ausgabe zum Vergleich mit der Tabelle Prognosewerte_Vergleichtabelle.ods
            #if i == Akt_Std:
            #    print("ACHTUNG: Im vorletzte Block sind die richtigen Werte zum Vergleich mit der Tabelle Prognosewerte_Vergleichtabelle.ods!!")
            #print("Std, Akt_Minute, Prognose, Pro_Uebersch:", i, Akt_Minute, int(Prognose), int(Pro_Uebersch))

            i  += 1


        # Hier noch den aktuellen Ladewert der Schleife ermitteln und im return mitgeben
        LadewertStd = datetime.strftime(now, format_aktStd)
        LadewertStd_naechste = datetime.strftime(now + timedelta(minutes = (60)), format_aktStd)

        Pro_Akt1 = (getPrognose(LadewertStd))
        Pro_Akt2 = (getPrognose(LadewertStd_naechste))

        # zu jeder Minute den genauen Zwischenwert mit den beiden Stundenprognosen rechnen
        Pro_Akt = int((Pro_Akt1 * (60 - Akt_Minute) + Pro_Akt2 * Akt_Minute) / 60)
        if ( Pro_Akt< 0): Pro_Akt = 0
        # print("Std, Pro_Akt1, Pro_Akt2, Pro_Akt: ", LadewertStd, Pro_Akt1, Pro_Akt2, Pro_Akt)

        # Nun den Aktuellen Ladewert rechnen 

        # BatSparFaktor aus der config.ini = Faktor um Batteriekapazitaet fuer spaeter zu sparen
        # Daempfungsfaktor rechnen 
        Stundendaempfung = (BattVollUm - Akt_Std - (Akt_Minute/60)) * BatSparFaktor
        if Stundendaempfung < 1:
            Stundendaempfung = 1

        # Batterieladewert mit allen Einfluessen aus der Prognose rechnen
        aktuellerLadewert = int((Pro_Akt - AbzugWatt)/Stundendaempfung)
        LadewertGrund = "Prognoseberechnung / Stundendaempfung"
        if aktuellerLadewert < 0: aktuellerLadewert = 0

        # BatWaitFaktor hier anwenden
        Tagessumme_Faktor = int((Pro_Ertrag_Tag - Grundlast_Sum) / (BatWaitFaktor_Max - BatWaitFaktor + 1))
        # BattStatusProz < 75; damit die Ladung nicht abschaltet, wenn die Batterie fast voll ist
        if Tagessumme_Faktor > BattKapaWatt_akt and BatWaitFaktor != 0 and BattStatusProz < 75 and Akt_Std < 13 :
            aktuellerLadewert = LadungAus
            LadewertGrund = "Tagesprognose / BatWaitFaktor > Batteriekapazitaet "

        # aktuelleBatteriePower ist beim Laden der Batterie minus
        # Wenn Einspeisung über Einspeisegrenze, dann könnte WR schon abregeln, desshalb Puffer_Einspeisegrenze addieren
        if aktuelleEinspeisung > Einspeisegrenze:
            EinspeisegrenzUeberschuss = int(aktuelleEinspeisung - aktuelleBatteriePower - Einspeisegrenze + Puffer_Einspeisegrenze)
        else:
            EinspeisegrenzUeberschuss = int(aktuelleEinspeisung - aktuelleBatteriePower - Einspeisegrenze)
        # Damit durch die Pufferaddition nicht die maximale PV_Leistung überschritten wird
        if EinspeisegrenzUeberschuss > PV_Leistung_Watt - Einspeisegrenze:
            EinspeisegrenzUeberschuss = PV_Leistung_Watt - Einspeisegrenze

        if EinspeisegrenzUeberschuss > aktuellerLadewert and (BattganzeLadeKapazWatt * oldPercent/10000) <= (MaxLadung + 100):
            aktuellerLadewert = int(EinspeisegrenzUeberschuss)
            LadewertGrund = "PV_Leistungsüberschuss > Einspeisegrenze"

        # Ladeleistung auf MaxLadung begrenzen
        if (aktuellerLadewert > MaxLadung):
            aktuellerLadewert = MaxLadung

        # Wenn  PV-Produktion + Puffer_WR_Kapazitaet > WR_Kapazitaet 
        if aktuellePVProduktion > WR_Kapazitaet:
            kapazitaetsueberschuss = int(aktuellePVProduktion - WR_Kapazitaet + Puffer_WR_Kapazitaet)
            if kapazitaetsueberschuss > PV_Leistung_Watt - WR_Kapazitaet:
                kapazitaetsueberschuss = PV_Leistung_Watt - WR_Kapazitaet
            if (kapazitaetsueberschuss > aktuellerLadewert ):
                aktuellerLadewert = kapazitaetsueberschuss
                LadewertGrund = "PV-Produktion > AC_Kapazitaet WR"

        # Bei Minuswerten "LadungAus" setzen
        if aktuellerLadewert < LadungAus:
            aktuellerLadewert = LadungAus


        return int(Pro_Uebersch_Tag), int(Pro_Ertrag_Tag), aktuellerLadewert, Grundlast_Sum, Pro_Spitze, Pro_Akt, LadewertGrund, Tagessumme_Faktor

def setLadewert(fun_Ladewert):
        if fun_Ladewert > MaxLadung:
            fun_Ladewert = MaxLadung

        newPercent = (int(fun_Ladewert/BattganzeLadeKapazWatt*10000))
        if newPercent < LadungAus:
            newPercent = LadungAus

        # Schaltvezögerung
        # mit altem Ladewert vergleichen
        diffLadewert_nachOben = int(fun_Ladewert - oldPercent*BattganzeLadeKapazWatt/10000)
        diffLadewert_nachUnten = int((oldPercent*BattganzeLadeKapazWatt/10000) - fun_Ladewert)

        # Wenn die Differenz in hundertstel Prozent kleiner als die Schreibgrenze nix schreiben
        newPercent_schreiben = 0
        if ( diffLadewert_nachOben > WRSchreibGrenze_nachOben ):
            newPercent_schreiben = 1
        if ( diffLadewert_nachUnten > WRSchreibGrenze_nachUnten ):
            newPercent_schreiben = 1

        # Wenn MaxLadung erstmals erreicht ist immer schreiben
        if (fun_Ladewert == MaxLadung) and (abs(diffLadewert_nachOben) > 3):
            newPercent_schreiben = 1

        return(newPercent, newPercent_schreiben)

if __name__ == '__main__':
        config = loadConfig('config.ini')
        now = datetime.now()
        format = "%Y-%m-%d %H:%M:%S"

        if ping(config['gen24']['hostNameOrIp']):
            # Nur ausführen, wenn WR erreichbar
            gen24 = None
            auto = False
            try:            
                    newPercent = None
    
                    ###############################
    
                    data = loadWeatherData(config)

                    # Reservierungsdatei lesen, wenn Reservierung eingeschaltet
                    PV_Reservierung_steuern = eval(config['Reservierung']['PV_Reservierung_steuern'])
                    if  PV_Reservierung_steuern == 1:
                        reservierungdata = loadPVReservierung(config)
                        # print(reservierungdata)

                    gen24 = SymoGen24Connector.SymoGen24(config['gen24']['hostNameOrIp'], config['gen24']['port'], auto)
                    # print(data)

                    if gen24.read_data('Battery_Status') == 1:
                        print(datetime.now())
                        print("Batterie ist Offline keine Steuerung möglich!!! ")
                        print()
                        exit()
    
                    # VARIABLENPRUEFUNG VERSION 9.1 
                    if not config.has_option('Ladeberechnung', 'Puffer_Einspeisegrenze' ) \
                    or not config.has_option('Ladeberechnung', 'PV_Leistung_Watt' ) \
                    or not config.has_option('Ladeberechnung', 'Puffer_WR_Kapazitaet' ):
                        print ('\nAb Version 9.1 werden in der config.ini die Variablen')
                        print ('  Puffer_Einspeisegrenze, PV_Leistung_Watt, Puffer_WR_Kapazitaet benötigt!')
                        print ('BITTE config.ini ergänzen! \n')
                        exit()
                    # ENDE VARIABLENPRUEFUNG VERSION 9.1 

                    # Benoetigte Variablen definieren
                    # Rechenwerte aus Config in Zahlen umwandeln
                    print_level = eval(config['Ladeberechnung']['print_level'])
                    BattVollUm = eval(config['Ladeberechnung']['BattVollUm'])
                    BatSparFaktor = eval(config['Ladeberechnung']['BatSparFaktor'])
                    BatWaitFaktor = eval(config['Ladeberechnung']['BatWaitFaktor'])
                    BatWaitFaktor_Max = eval(config['Ladeberechnung']['BatWaitFaktor_Max'])
                    MaxLadung = eval(config['Ladeberechnung']['MaxLadung'])
                    LadungAus = eval(config['Ladeberechnung']['LadungAus'])
                    Einspeisegrenze = eval(config['Ladeberechnung']['Einspeisegrenze'])
                    WR_Kapazitaet = eval(config['Ladeberechnung']['WR_Kapazitaet'])
                    Puffer_Einspeisegrenze = eval(config['Ladeberechnung']['Puffer_Einspeisegrenze'])
                    PV_Leistung_Watt = eval(config['Ladeberechnung']['PV_Leistung_Watt'])
                    Puffer_WR_Kapazitaet = eval(config['Ladeberechnung']['Puffer_WR_Kapazitaet'])
                    Grundlast = eval(config['Ladeberechnung']['Grundlast'])
                    MindBattLad = eval(config['Ladeberechnung']['MindBattLad'])
                    BatterieVoll = eval(config['Ladeberechnung']['BatterieVoll'])
                    WRSchreibGrenze_nachOben = eval(config['Ladeberechnung']['WRSchreibGrenze_nachOben'])
                    WRSchreibGrenze_nachUnten = eval(config['Ladeberechnung']['WRSchreibGrenze_nachUnten'])
                    FesteLadeleistung = eval(config['Ladeberechnung']['FesteLadeleistung'])
                    Fallback_on = eval(config['Fallback']['Fallback_on'])
                    Cronjob_Minutenabstand = eval(config['Fallback']['Cronjob_Minutenabstand'])
                    Fallback_Zeitabstand_Std = eval(config['Fallback']['Fallback_Zeitabstand_Std'])
                    BattganzeLadeKapazWatt = (gen24.read_data('BatteryChargeRate')) + 1  # +1 damit keine Divison duch Null entstehen kann
                    BattganzeKapazWatt = (gen24.read_data('Battery_capa')) + 1  # +1 damit keine Divison duch Null entstehen kann
                    BattStatusProz = gen24.read_data('Battery_SoC')/100
                    BattKapaWatt_akt = int((1 - BattStatusProz/100) * BattganzeKapazWatt)
                    aktuelleEinspeisung = int(gen24.get_meter_power() * -1)
                    aktuellePVProduktion = int(gen24.get_mppt_power())
                    aktuelleBatteriePower = int(gen24.get_batterie_power())
                    BatteryMaxDischargePercent = int(gen24.read_data('BatteryMaxDischargePercent')/100) 
                    Push_Message_EIN = eval(config['messaging']['Push_Message_EIN'])
                    Push_Message_Url = config['messaging']['Push_Message_Url']

                    # 0 = nicht auf WR schreiben, 1 = schon auf WR schreiben
                    newPercent_schreiben = 0
                    oldPercent = gen24.read_data('BatteryMaxChargePercent')
                    alterLadewert = int(oldPercent*BattganzeLadeKapazWatt/10000)
    
                    format_aktStd = "%Y-%m-%d %H:00:00"
    
    
                    #######################################
                    ## Ab hier gehts los wie Ablaufdiagramm
                    #######################################
    
                    Schleifenwert_TagesPrognoseUeberschuss = 1000000
                    TagesPrognoseUeberschuss = 0
                    TagesPrognoseGesamt = 0
                    aktuellerLadewert = 0
                    PrognoseAbzugswert = 0
                    Grundlast_Summe = 0
                    Pro_Spitze = 0
                    aktuelleVorhersage = 0
                    LadewertGrund = ""
                    Tagessumme_Faktor = 0
                        
                    # Abzugswert sollte nicht kleiner Grundlast sein, sonnst wird PV-Leistung zur Ladung der Batterie berechnet,
                    # die durch die Grundlast im Haus verbraucht wird. => Batterie wird nicht voll
                    i = Grundlast
                    # Gesamte Tagesprognose, Tagesüberschuß aus Prognose und aktuellen Ladewert ermitteln
                    # Schleife laeft von 0 nach oben, bis der Prognoseueberschuss die aktuelle Batteriekapazietaet erreicht
                    while (Schleifenwert_TagesPrognoseUeberschuss > BattKapaWatt_akt):
                        PrognoseUNDUeberschuss = getRestTagesPrognoseUeberschuss( i, aktuelleEinspeisung, aktuellePVProduktion )
                        Schleifenwert_TagesPrognoseUeberschuss = PrognoseUNDUeberschuss[0]
                        if(PrognoseUNDUeberschuss[0] >= BattKapaWatt_akt) or (i == Grundlast):
                            PrognoseAbzugswert = i
                            TagesPrognoseUeberschuss = PrognoseUNDUeberschuss[0]
                            TagesPrognoseGesamt = PrognoseUNDUeberschuss[1]
                            aktuellerLadewert = PrognoseUNDUeberschuss[2]
                            Grundlast_Summe = PrognoseUNDUeberschuss[3]
                            Pro_Spitze = PrognoseUNDUeberschuss[4]
                            aktuelleVorhersage = PrognoseUNDUeberschuss[5]
                            LadewertGrund = PrognoseUNDUeberschuss[6]
                            Tagessumme_Faktor = PrognoseUNDUeberschuss[7]
                        i += 100
                    # Nun habe ich die Werte und muss hier Verzweigen
    
                    # Wenn über die PV-Planung Volle Ladung angewählt wurde
                    MaxladungDurchPV_Planung = ""
                    if (PV_Reservierung_steuern == 1) and (reservierungdata.get('ManuelleSteuerung')):
                        FesteLadeleistung = MaxLadung * reservierungdata.get('ManuelleSteuerung')
                        if (reservierungdata.get('ManuelleSteuerung') != 0):
                            MaxladungDurchPV_Planung = "Manuelle Ladesteuerung in PV-Planung ausgewählt."

                    # Wenn die Variable "FesteLadeleistung" größer "0" ist, wird der Wert fest als Ladeleistung in Watt geschrieben einstellbare Wattzahl
                    if FesteLadeleistung > 0:
                        DATA = setLadewert(FesteLadeleistung)
                        aktuellerLadewert = FesteLadeleistung
                        newPercent = DATA[0]
                        if newPercent == oldPercent:
                            newPercent_schreiben = 0
                        else:
                            newPercent_schreiben = 1
                        if MaxladungDurchPV_Planung == "":
                            LadewertGrund = "FesteLadeleistung"
                        else:
                            LadewertGrund = MaxladungDurchPV_Planung
    
                    else:

                        # Schaltverzögerung für MindBattLad
                        if (alterLadewert+2 > MaxLadung):
                            MindBattLad = MindBattLad +5
                        # print("MaxLadung, alterLadewert, MindBattLad:", MaxLadung, alterLadewert, MindBattLad)

                        if ((BattStatusProz < MindBattLad)):
                            # volle Ladung ;-)
                            aktuellerLadewert = MaxLadung
                            DATA = setLadewert(MaxLadung)
                            newPercent = DATA[0]
                            newPercent_schreiben = DATA[1]
                            LadewertGrund = "BattStatusProz < MindBattLad"
    
                        else:
    
                            if (TagesPrognoseGesamt > Grundlast) and ((TagesPrognoseGesamt - Grundlast_Summe) < BattKapaWatt_akt):
                                # Auch hier die Schaltverzögerung anbringen und dann MaxLadung, also immer nach oben.
                                if BattKapaWatt_akt + Grundlast_Summe - TagesPrognoseGesamt < WRSchreibGrenze_nachOben:
                                    # Nach Prognoseberechnung darf es trotzdem nach oben gehen aber nicht von MaxLadung nach unten !
                                    WRSchreibGrenze_nachUnten = 100000
                                    DATA = setLadewert(aktuellerLadewert)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    # Nur wenn newPercent_schreiben = 0 dann LadewertGrund mit Hinweis übreschreiben
                                    if newPercent_schreiben == 0:
                                        LadewertGrund = " TagesPrognoseGesamt - Grundlast_Summe < BattKapaWatt_akt (Unterschied weniger als Schreibgrenze)"
                                else:
                                    # volle Ladung ;-)
                                    aktuellerLadewert = MaxLadung
                                    DATA = setLadewert(MaxLadung)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    LadewertGrund = "TagesPrognoseGesamt - Grundlast_Summe < BattKapaWatt_akt"
    
                            elif (BattStatusProz > BatterieVoll ):
                                # Wenn Batterie voll, Volle Ladung
                                aktuellerLadewert = MaxLadung
                                DATA = setLadewert(aktuellerLadewert)
                                newPercent = DATA[0]
                                newPercent_schreiben = DATA[1]
                                LadewertGrund = "           Batterie fast voll!!"
        
                            # PrognoseAbzugswert - 100 um Schaltverzögerung wieder nach unten zu erreichen
                            elif (TagesPrognoseUeberschuss < BattKapaWatt_akt) or (PrognoseAbzugswert - 100 <= Grundlast):
                                # Auch hier die Schaltverzögerung anbringen und dann MaxLadung, also immer nach oben.
                                if BattKapaWatt_akt - TagesPrognoseUeberschuss < WRSchreibGrenze_nachOben:
                                    # Nach Prognoseberechnung darf es trotzdem nach oben gehen aber nicht von MaxLadung nach unten !
                                    WRSchreibGrenze_nachUnten = 100000
                                    DATA = setLadewert(aktuellerLadewert)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    # Nur wenn newPercent_schreiben = 0 dann LadewertGrund mit Hinweis übreschreiben
                                    if newPercent_schreiben == 0:
                                        LadewertGrund = "PrognoseAbzugswert nahe Grundlast (Unterschied weniger als Schreibgrenze)"
                                else:
                                    # volle Ladung ;-)
                                    aktuellerLadewert = MaxLadung
                                    DATA = setLadewert(MaxLadung)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    LadewertGrund = "PrognoseAbzugswert kleiner Grundlast und Schreibgrenze"
                            else: 
                                DATA = setLadewert(aktuellerLadewert)
                                newPercent = DATA[0]
                                newPercent_schreiben = DATA[1]

                

                    if print_level == 1:
                        try:
                            print("************* BEGINN: ", datetime.now(),"************* ")
                            print("\n######### L A D E S T E U E R U N G #########\n")
                            print("aktuellePrognose:           ", aktuelleVorhersage)
                            print("RestTagesPrognose:          ", TagesPrognoseGesamt)
                            print("PrognoseAbzugswert/Stunde:  ", PrognoseAbzugswert)
                            print("TagesPrognose - Abzugswerte:", TagesPrognoseUeberschuss)
                            print("Tagessumme/BatWaitFaktor:   ", Tagessumme_Faktor)
                            print("Grundlast_Summe für Tag:    ", Grundlast_Summe)
                            print("aktuellePVProduktion/Watt:  ", aktuellePVProduktion)
                            print("aktuelleEinspeisung/Watt:   ", aktuelleEinspeisung)
                            print("aktuelleBatteriePower/Watt: ", aktuelleBatteriePower)
                            print("aktuelleBattKapazität/Watt: ", BattKapaWatt_akt)
                            print("LadewertGrund: ", LadewertGrund)
                            print("Bisheriger Ladewert/Watt:   ", alterLadewert)
                            print("Bisheriger Ladewert/Prozent:", oldPercent/100,"%")
                            print("Neuer Ladewert/Watt:        ", aktuellerLadewert)
                            print("Neuer Ladewert/Prozent:     ", newPercent/100,"%")
                            print("newPercent_schreiben:       ", newPercent_schreiben)
                            # dataBatteryStats = gen24.read_section('StorageDevice')
                            # print(f'Battery Stats: {dataBatteryStats}') 
                            print()
                        except Exception as e:
                            print()
                            print("Fehler in den Printbefehlen, Ausgabe nicht möglich!")
                            print("Fehlermeldung:", e)
                            print()



                    ### AB HIER SCHARF wenn Argument "schreiben" übergeben

                    bereits_geschrieben = 0
                    Schreib_Ausgabe = ""
                    Push_Schreib_Ausgabe = ""
                    # Neuen Ladewert in Prozent schreiben, wenn newPercent_schreiben == 1
                    if newPercent_schreiben == 1:
                        if len(argv) > 1 and (argv[1] == "schreiben"):
                            valueNew = gen24.write_data('BatteryMaxChargePercent', newPercent)
                            bereits_geschrieben = 1
                            Schreib_Ausgabe = Schreib_Ausgabe + "Folgender Wert wurde geschrieben: " + str(newPercent) + "\n"
                            Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "Es wurde nix geschrieben, da NICHT \"schreiben\" übergeben wurde: \n"
                    else:
                        Schreib_Ausgabe = Schreib_Ausgabe + "Alte und Neue Werte unterscheiden sich weniger als die Schreibgrenzen des WR, NICHTS zu schreiben!!\n"

                    # Ladungsspeichersteuerungsmodus aktivieren wenn nicht aktiv
                    # kann durch Fallback (z.B. nachts) erfordelich sein, ohne dass Änderung an der Ladeleistung nötig ist
                    if gen24.read_data('StorageControlMode') != 3:
                        if len(argv) > 1 and (argv[1] == "schreiben"):
                            Ladelimit = gen24.write_data('StorageControlMode', 3 )
                            bereits_geschrieben = 1
                            Schreib_Ausgabe = Schreib_Ausgabe + "StorageControlMode neu geschrieben.\n"
                            Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe 
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "StorageControlMode neu wurde NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"

                    if print_level == 1:
                        print(Schreib_Ausgabe)
    
                    ######## E N T L A D E S T E U E R U N G  ab hier wenn eingeschaltet!

                    Batterieentlandung_steuern = eval(config['Reservierung']['Batterieentlandung_steuern'])
                    if  Batterieentlandung_steuern == 1 and PV_Reservierung_steuern == 1:
                        print("######### E N T L A D E S T E U E R U N G #########\n")
                        # Variablen bereitstellen
                        BisLadestandEIN = eval(config['Reservierung']['BisLadestandEIN'])
                        AbReservierungEIN = eval(config['Reservierung']['AbReservierungEIN'])
                        MaxEntladung = eval(config['Reservierung']['MaxEntladung'])
                        EntladungAus = eval(config['Reservierung']['EntladungAus'])
                        GesamtverbrauchHaus = aktuellePVProduktion - aktuelleEinspeisung + aktuelleBatteriePower
                        aktStd = datetime.strftime(now, format_aktStd)

                        if (reservierungdata.get(aktStd)):
                            ReservierteWatt = reservierungdata[aktStd]
                        else:
                            ReservierteWatt = 0

                        ## Werte zum Überprüfen ausgeben
                        print("Batteriestatus in Prozent: ", BattStatusProz)
                        print("BisLadestandEIN: ", BisLadestandEIN)
                        print("Gesamtverbrauch Haus: ", GesamtverbrauchHaus)
                        print("Reservierung Watt: ", ReservierteWatt)
                        print("AbReservierungEIN: ", AbReservierungEIN)
                        print("Batterieentladegrenze in %: ", BatteryMaxDischargePercent)
                        print()

                        # Wenn folgende Bedingungen wahr, Entladung ausschalten
                        # Schaltverzögerung berechnen und anbringen.
                        Entladung_Daempfung = 5 - BatteryMaxDischargePercent/100*5
                        if (BattStatusProz < (BisLadestandEIN + Entladung_Daempfung)) and (GesamtverbrauchHaus > ReservierteWatt * 0.9) and (ReservierteWatt > AbReservierungEIN):
                            Neu_BatteryMaxDischargePercent = EntladungAus
                        else:
                            Neu_BatteryMaxDischargePercent = MaxEntladung

                        Schreib_Ausgabe = ""

                        if (Neu_BatteryMaxDischargePercent != BatteryMaxDischargePercent):
                            if len(argv) > 1 and (argv[1] == "schreiben"):
                                valueNew = gen24.write_data('BatteryMaxDischargePercent', Neu_BatteryMaxDischargePercent * 100)
                                Schreib_Ausgabe = Schreib_Ausgabe + "Folgender Wert wurde geschrieben für Batterieentladung: " + str(Neu_BatteryMaxDischargePercent) + "%\n"
                                Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe 
                            else:
                                Schreib_Ausgabe = Schreib_Ausgabe + "Für Batterieentladung wurde NICHT " + str(Neu_BatteryMaxDischargePercent) +"% geschrieben, da NICHT \"schreiben\" übergeben wurde: \n"
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "Alte und Neue Werte der Batterieentladung ("+ str(Neu_BatteryMaxDischargePercent) + "%) sind identisch, NICHTS zu schreiben!!\n"

                        if print_level == 1:
                            print(Schreib_Ausgabe)

                    # Wenn Pushmeldung aktiviert und Daten geschrieben an Dienst schicken
                    if (Push_Schreib_Ausgabe != "") and (Push_Message_EIN == 1):
                        apiResponse = requests.post(Push_Message_Url, data=Push_Schreib_Ausgabe.encode(encoding='utf-8'), headers={ "Title": "Meldung Batterieladesteuerung!", "Tags": "sunny,zap" })
                        print("PushMeldung an ", Push_Message_Url, " gesendet.")


                    ######## PV Reservierung ENDE


                    # FALLBACK des Wechselrichters bei Ausfall der Steuerung
                    if Fallback_on != 0:
                        Fallback_Schreib_Ausgabe = ""
                        akt_Fallback_time = gen24.read_data('InOutWRte_RvrtTms_Fallback')
                        if Fallback_on == 2:
                            Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback ist eingeschaltet.\n"
                            Akt_Zeit_Rest = int(datetime.strftime(now, "%H%M")) % (Fallback_Zeitabstand_Std*100)
                            Fallback_Sekunden = int((Fallback_Zeitabstand_Std * 3600) + (Cronjob_Minutenabstand * 60 * 0.9))
                            # Zur vollen Fallbackstunde wenn noch kein Schreibzugriff war Fallback schreiben
                            if Akt_Zeit_Rest == 0 or akt_Fallback_time != Fallback_Sekunden:
                                if bereits_geschrieben == 0 or akt_Fallback_time != Fallback_Sekunden:
                                    if len(argv) > 1 and (argv[1] == "schreiben"):
                                        fallback_msg = gen24.write_data('InOutWRte_RvrtTms_Fallback', Fallback_Sekunden)
                                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback geschrieben.\n"
                                    else:
                                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback wurde NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"
                                else:
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback wurde NICHT geschrieben, da bereits auf den WR geschrieben wurde.\n"

                        else:
                            Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback ist NICHT eingeschaltet.\n"
                            if akt_Fallback_time != 0:
                                if len(argv) > 1 and (argv[1] == "schreiben"):
                                    fallback_msg = gen24.write_data('InOutWRte_RvrtTms_Fallback', 0)
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback Deaktivierung geschrieben.\n"
                                else:
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback Deaktivierung NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"

                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "InOutWRte_RvrtTms_Fallback: " + str(gen24.read_data('InOutWRte_RvrtTms_Fallback')) + "\n"
                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "StorageControlMode:    " + str(gen24.read_data('StorageControlMode')) + "\n"

                        if print_level == 1:
                            print(Fallback_Schreib_Ausgabe)
                    # FALLBACK ENDE
                    print("************* ENDE: ", datetime.now(),"************* \n")


            finally:
                    if (gen24 and not auto):
                            gen24.modbus.close()


        else:
            print(datetime.now())
            print("WR offline")

