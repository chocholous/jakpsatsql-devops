f = open("logins.sql", "w")
f.write("--this is generated login file \n")



dbname = "COURSES"
cg={ \
  "NODES": [

    {"NAME" : "CZECHITA",
     "LOGINS" : [   
         {"username": "TEST24", "email": "pavel@chocholous.net"},
         {"username": "SUSTROVAM", "email": "vase_marie@volny.cz"},
         {"username": "AMBRUSOVAT", "email": "t.ambrusova@gmail.com"},
         {"username": "ANTOSOVAD", "email": "d.antosova@gmail.com"},
         {"username": "DVORACKOVAV", "email": "vendula.dvorackova.vd@gmail.com"},
         {"username": "ERZINAM", "email": "erzinamr@gmail.com"},
         {"username": "HAJKOVAK", "email": "karen.hajkova@gmail.com"},
         {"username": "KARMINOVAE", "email": "karminova.edita@gmail.com"},
         {"username": "KARTAKOVAT", "email": "kartakovat@gmail.com"},
         {"username": "KOCANDOVAA", "email": "alena.rezacova@gmail.com"},
         {"username": "KOLARIKOVAL", "email": "lucia.j.kolarikova@gmail.com"},
         {"username": "KOLIASOVAN", "email": "nelakoliasova@gmail.com"},
         {"username": "KOUDELKOVAL", "email": "lenkakoudelkova2@gmail.com"},
         {"username": "KRALICKOVAZ", "email": "zuzkaalx@gmail.com"},
         {"username": "KRIZKOVAM", "email": "maegda83@gmail.com"},
         {"username": "KUMPEROVAK", "email": "katerinakumperova010@gmail.com"},
         {"username": "KUSHNIRV", "email": "viktorkaua777@gmail.com"},
         {"username": "LUKESOVAP", "email": "lukesova.pavlina@gmail.com"},
         {"username": "MAKOVSKAR", "email": "romana.makovska@gmail.com"},
         {"username": "MARJENKOVAN", "email": "vargova.nikolka@gmail.com"},
         {"username": "MAZANKOVAK", "email": "mazankok1998@gmail.com"},
         {"username": "MIHALIKOVAS", "email": "silvamihalik@gmail.com"},
         {"username": "MOZHAROVAA", "email": "mozharova.nas@gmail.com"},
         {"username": "NGUYENT", "email": "trami.nguyen392@gmail.com"},
         {"username": "PAKOSTOVAI", "email": "Ifca.Gabi@gmail.com"},
         {"username": "PAVELKOVAA", "email": "ann.pavelkova@gmail.com"},
         {"username": "PAZDZIOROVAI", "email": "ivana.pazdziorova@gmail.com"},
         {"username": "PRIBILOVAZ", "email": "zuzana.pribilova@gmail.com"},
         {"username": "RUZICKOVAH", "email": "hana.forstova@gmail.com"},
         {"username": "RUZICKOVAS", "email": "stepa.ruzickova@gmail.com"},
         {"username": "SIMERSKAM", "email": "msimerska@gmail.com"},
         {"username": "SMONDRKZ", "email": "zuzana.smondrk@gmail.com"},
         {"username": "SUSKOVAM", "email": "martina.suskova93@gmail.com"},
         {"username": "VAVROVAL", "email": "vavrlenk@gmail.com"},
         {"username": "VRBASOVAK", "email": "vrbasovak@gmail.com"},
         {"username": "ZIKMUNDOVAL", "email": "lazzikmundova@gmail.com"},       ]
    }
],
"COACHES": [
{"username": "KOUC", "email": "pavel@chocholous.net"}, 
]
    }

#jeden kouc ;)
f.write("CREATE OR REPLACE ROLE ROLE_SUPERKOUC; \n" \
       "GRANT ROLE ROLE_SUPERKOUC TO USER sfadmin; \n"
       "CREATE OR REPLACE ROLE ROLE_KOUC; \n" \
       "GRANT USAGE ON DATABASE COURSES TO ROLE ROLE_KOUC; \n" \
       "/* * * * * * * *  * * * * **********************************/ \n"
      )
#a dalsi kouci
f.write("--VYTVORENI KOUCU")
for c in cg["COACHES"]:
    u = c["username"]
    e = c["email"]
    f.write("CREATE OR REPLACE USER KOUC_"+u+" PASSWORD = 'SpANEKSeNePRECENUJE', EMAIL = '"+e+"', MUST_CHANGE_PASSWORD = TRUE, DEFAULT_WAREHOUSE = 'COMPUTE_WH', DEFAULT_NAMESPACE = '" + dbname +".PUBLIC', DEFAULT_ROLE = 'ROLE_KOUC'; \n")
    f.write("GRANT ROLE ROLE_KOUC TO USER KOUC_"+u+"; \n")
f.write("\n")
#create user ondra password = 'SPANEKSENEPRECENUJE', email = 'HOSAK@AVAST.COM', must_change_password = true, DEFAULT_WAREHOUSE = 'COMPUTE_WH', DEFAULT_NAMESPACE = 'CHOCHOLOUSP.PUBLIC', DEFAULT_ROLE = 'EXT_ADMIN';

#vytvoreni schemat a roli pro kazdy node
f.write("--USER LOGIN, SCHEMA, ROLE \n")
for node in cg["NODES"]:
    n = node["NAME"]
    f.write("-- VYTVORENI SCHEMAT A ROLI NODE "+n+"; \n"          
          "CREATE OR REPLACE ROLE ROLE_"+n+"; \n" \
          "CREATE OR REPLACE ROLE ROLE_"+n+"_KOUC; \n" \
          "CREATE OR REPLACE SCHEMA SCH_"+n+"; \n"
          "CREATE OR REPLACE SCHEMA SCH_"+n+"_HRISTE; \n")
    #vytvoreni teroru
    f.write("create or replace TABLE SCH_"+n+".TEROR_DPJ22 (   EVENTID NUMBER(38,0),   IYEAR NUMBER(38,0),   IMONTH NUMBER(38,0),   IDAY NUMBER(38,0),   APPROXDATE VARCHAR(16777216),   EXTENDED NUMBER(38,0),   RESOLUTION NUMBER(38,0),   COUNTRY NUMBER(38,0),   COUNTRY_TXT VARCHAR(16777216),   REGION NUMBER(38,0),   REGION_TXT VARCHAR(16777216),   PROVSTATE VARCHAR(16777216),   CITY VARCHAR(16777216),   LATITUDE NUMBER(12,8),   LONGITUDE NUMBER(12,8),   SPECIFICITY NUMBER(38,0),   VICINITY NUMBER(38,0),   LOCATION VARCHAR(16777216),   SUMMARY VARCHAR(16777216),   CRIT1 NUMBER(38,0),   CRIT2 NUMBER(38,0),   CRIT3 NUMBER(38,0),   DOUBTTERR NUMBER(38,0),   ALTERNATIVE NUMBER(38,0),   ALTERNATIVE_TXT VARCHAR(16777216),   MULTIPLE NUMBER(38,0),   SUCCESS NUMBER(38,0),   SUICIDE NUMBER(38,0),   ATTACKTYPE1 NUMBER(38,0),   ATTACKTYPE1_TXT VARCHAR(16777216),   ATTACKTYPE2 NUMBER(38,0),   ATTACKTYPE2_TXT VARCHAR(16777216),   ATTACKTYPE3 NUMBER(38,0),   ATTACKTYPE3_TXT VARCHAR(16777216),   TARGTYPE1 NUMBER(38,0),   TARGTYPE1_TXT VARCHAR(16777216),   TARGSUBTYPE1 NUMBER(38,0),   TARGSUBTYPE1_TXT VARCHAR(16777216),   CORP1 VARCHAR(16777216),   TARGET1 VARCHAR(16777216),   NATLTY1 NUMBER(38,0),   NATLTY1_TXT VARCHAR(16777216),   TARGTYPE2 NUMBER(38,0),   TARGTYPE2_TXT VARCHAR(16777216),   TARGSUBTYPE2 NUMBER(38,0),   TARGSUBTYPE2_TXT VARCHAR(16777216),   CORP2 VARCHAR(16777216),   TARGET2 VARCHAR(16777216),   NATLTY2 NUMBER(38,0),   NATLTY2_TXT VARCHAR(16777216),   TARGTYPE3 NUMBER(38,0),   TARGTYPE3_TXT VARCHAR(16777216),   TARGSUBTYPE3 NUMBER(38,0),   TARGSUBTYPE3_TXT VARCHAR(16777216),   CORP3 VARCHAR(16777216),   TARGET3 VARCHAR(16777216),   NATLTY3 NUMBER(38,0),   NATLTY3_TXT VARCHAR(16777216),   GNAME VARCHAR(16777216),   GSUBNAME VARCHAR(16777216),   GNAME2 VARCHAR(16777216),   GSUBNAME2 VARCHAR(16777216),   GNAME3 VARCHAR(16777216),   GSUBNAME3 VARCHAR(16777216),   MOTIVE VARCHAR(16777216),   GUNCERTAIN1 NUMBER(38,0),   GUNCERTAIN2 NUMBER(38,0),   GUNCERTAIN3 NUMBER(38,0),   INDIVIDUAL NUMBER(38,0),   NPERPS NUMBER(38,0),   NPERPCAP NUMBER(38,0),   CLAIMED NUMBER(38,0),   CLAIMMODE NUMBER(38,0),   CLAIMMODE_TXT VARCHAR(16777216),   CLAIM2 VARCHAR(16777216),   CLAIMMODE2 VARCHAR(16777216),   CLAIMMODE2_TXT VARCHAR(16777216),   CLAIM3 VARCHAR(16777216),   CLAIMMODE3 VARCHAR(16777216),   CLAIMMODE3_TXT VARCHAR(16777216),   COMPCLAIM VARCHAR(16777216),   WEAPTYPE1 NUMBER(38,0),   WEAPTYPE1_TXT VARCHAR(16777216),   WEAPSUBTYPE1 NUMBER(38,0),   WEAPSUBTYPE1_TXT VARCHAR(16777216),   WEAPTYPE2 NUMBER(38,0),   WEAPTYPE2_TXT VARCHAR(16777216),   WEAPSUBTYPE2 NUMBER(38,0),   WEAPSUBTYPE2_TXT VARCHAR(16777216),   WEAPTYPE3 NUMBER(38,0),   WEAPTYPE3_TXT VARCHAR(16777216),   WEAPSUBTYPE3 NUMBER(38,0),   WEAPSUBTYPE3_TXT VARCHAR(16777216),   WEAPTYPE4 NUMBER(38,0),   WEAPTYPE4_TXT VARCHAR(16777216),   WEAPSUBTYPE4 NUMBER(38,0),   WEAPSUBTYPE4_TXT VARCHAR(16777216),   WEAPDETAIL VARCHAR(16777216),   NKILL NUMBER(38,0),   NKILLUS NUMBER(38,0),   NKILLTER NUMBER(38,0),   NWOUND NUMBER(38,0),   NWOUNDUS NUMBER(38,0),   NWOUNDTE NUMBER(38,0),   PROPERTY NUMBER(38,0),   PROPEXTENT NUMBER(38,0),   PROPEXTENT_TXT VARCHAR(16777216),   PROPVALUE NUMBER(38,0),   PROPCOMMENT VARCHAR(16777216),   ISHOSTKID NUMBER(38,0),   NHOSTKID NUMBER(38,0),   NHOSTKIDUS NUMBER(38,0),   NHOURS NUMBER(38,0),   NDAYS NUMBER(38,0),   DIVERT VARCHAR(16777216),   KIDHIJCOUNTRY VARCHAR(16777216),   RANSOM NUMBER(38,0),   RANSOMAMT NUMBER(16,4),   RANSOMAMTUS NUMBER(16,4),   RANSOMPAID NUMBER(16,4),   RANSOMPAIDUS NUMBER(16,4),   RANSOMNOTE VARCHAR(16777216),   HOSTKIDOUTCOME NUMBER(38,0),   HOSTKIDOUTCOME_TXT VARCHAR(16777216),   NRELEASED NUMBER(38,0),   ADDNOTES VARCHAR(16777216),   SCITE1 VARCHAR(16777216),   SCITE2 VARCHAR(16777216),   SCITE3 VARCHAR(16777216),   DBSOURCE VARCHAR(16777216),   INT_LOG NUMBER(38,0),   INT_IDEO NUMBER(38,0),   INT_MISC NUMBER(38,0),   INT_ANY NUMBER(38,0),   RELATED VARCHAR(16777216)  ); \n")
    lLogins = node["LOGINS"]
    for cred in lLogins:
        u = cred["username"]
        e = cred["email"]
        f.write(" \n" \
        "CREATE OR REPLACE ROLE ROLE_"+n+"_"+u+";\n" \
        "CREATE OR REPLACE SCHEMA SCH_"+n+"_"+u+";\n" \
        "CREATE OR REPLACE USER "+n+"_"+u+" PASSWORD = 'SpANEKSePrECENUJE', EMAIL = '"+e+"', MUST_CHANGE_PASSWORD = TRUE, DEFAULT_WAREHOUSE = 'COMPUTE_WH', DEFAULT_NAMESPACE = '" + dbname + ".SCH_" +n+"', DEFAULT_ROLE = 'ROLE_"+n+"_"+u+"'; \n" \
        )
#granty
for node in cg["NODES"]:
    n = node["NAME"]
    f.write("-- GRANTNUTI PRAV KOUCUM PRO NODE "+n+"; \n"
           "GRANT ROLE ROLE_"+n+"_KOUC TO ROLE ROLE_SUPERKOUC; \n" \
     "GRANT ROLE ROLE_"+n+" TO ROLE ROLE_"+n+"_KOUC; \n" )
f.write(" /*UNCOMMENT AT WILL \n")
for node in cg["NODES"]:
    n = node["NAME"]
    f.write("-- ROLES FOR " + n + "\n")
    for c in cg["COACHES"]:
        u = c["username"]
        f.write("" \
        "GRANT ROLE ROLE_"+n+"_KOUC TO USER KOUC_"+u+"; \n")
f.write("UNCOMMENT AT WILL */ \n")

f.write("\n--GRANT SELECT ON SCHEMAS TO ROLES \n")
for node in cg["NODES"]:
    n = node["NAME"]
    f.write("GRANT USAGE ON DATABASE COURSES TO ROLE ROLE_"+n+"; \n" \
    "GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE ROLE_"+n+"; \n" \
    "GRANT USAGE ON SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"; \n" \
    "GRANT SELECT ON ALL TABLES IN SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"; \n" \
    "GRANT SELECT ON FUTURE TABLES IN SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"; \n" \
    "GRANT USAGE ON SCHEMA SCH_"+n+"_HRISTE TO ROLE ROLE_"+n+"; \n" \
    "GRANT SELECT ON ALL TABLES IN SCHEMA SCH_"+n+"_HRISTE TO ROLE ROLE_"+n+"; \n" \
    "GRANT SELECT ON FUTURE TABLES IN SCHEMA SCH_"+n+"_HRISTE TO ROLE ROLE_"+n+"; \n" \
    "GRANT ALL ON SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"_KOUC; \n"
    "GRANT ALL ON ALL TABLES IN SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"_KOUC; \n"
    "GRANT ALL ON FUTURE TABLES IN SCHEMA SCH_"+n+" TO ROLE ROLE_"+n+"_KOUC; \n \n")
    for cred in node["LOGINS"]:
        u = cred["username"]
        f.write("GRANT ROLE ROLE_"+n+" TO ROLE ROLE_"+n+"_"+u+";\n")

for node in cg["NODES"]:
    n = node["NAME"]
    for cred in node["LOGINS"]:
        u = cred["username"]
        f.write("GRANT ALL ON SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_"+u+"; \n" \
        "GRANT ROLE ROLE_"+n+"_"+u+" TO USER "+n+"_"+u+"; \n" \
        "GRANT ALL ON ALL TABLES IN SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_"+u+"; \n" \
        "GRANT ALL ON FUTURE TABLES IN SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_"+u+"; \n" \
        "GRANT ALL ON SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_KOUC; \n" \
        "GRANT ALL ON FUTURE TABLES IN SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_KOUC; \n"
        "GRANT ALL ON ALL TABLES IN SCHEMA SCH_"+n+"_"+u+" TO ROLE ROLE_"+n+"_KOUC; \n" )
#create schema $schema
# role
# ownership
# hriste
# testdata
# clenstvi v role_czechita


f.close()