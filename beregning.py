import numpy
import system
import geometri
import laster
import klima
import tilstand
import TEST
import deformasjon


def _beregn_reaksjonskrefter(F):
    """Beregner reaksjonskrefter og plasserer bidragene i riktig rad
    og kolonne i R-matrisen."""

    # Initierer R-matrisen for reaksjonskrefter
    R = numpy.zeros((15, 6))

    for j in F:
        R_0 = numpy.zeros((15, 6))
        f = j.f
        if not numpy.count_nonzero(j.q) == 0:
            f = numpy.array([j.q[0] * j.b, j.q[1] * j.b, j.q[2] * j.b])

        # Sorterer bidrag til reaksjonskrefter
        R_0[j.type][0] = (f[0] * j.e[2]) + (f[2] * -j.e[0])
        R_0[j.type][1] = f[1]
        R_0[j.type][2] = (f[0] * -j.e[1]) + (f[1] * j.e[0])
        R_0[j.type][3] = f[2]
        R_0[j.type][4] = f[0]
        R_0[j.type][5] = abs(f[1] * -j.e[2]) + abs(f[2] * j.e[1])
        R += R_0

    return R


def _beregn_deformasjoner(i, sys, mast, F, sidekrefter):
    """Beregner deformasjoner og plasserer bidragene
     i riktig rad og kolonne i D-matrisen.
    """

    # Initerer deformasjonsmatrisen, D
    D = numpy.zeros((15, 3))

    for j in F:
        D_0 = numpy.zeros((15, 3))

        D_0 += deformasjon.bjelkeformel_M(mast, j, i.fh) \
            + deformasjon.bjelkeformel_P(mast, j, i.fh) \
            + deformasjon.bjelkeformel_q(mast, j, i.fh)

        if mast.type == "bjelke":
            D_0 += deformasjon.torsjonsvinkel(mast, j, i)

        D += D_0

    D += deformasjon.utliggerbidrag(sys, sidekrefter)

    return D


def beregn(i):
    import mast

    # R = reaksjonskrefter ved mastens innspenning
    #
    #              R
    #
    #          Indekser:
    #   0   1   2   3   4   5
    #   My  Vy  Mz  Vz  N   T
    #  ________________________
    # |                        | 0  Egenvekt (mast, utligger, ledninger)
    # |                        | 1  Kontaktledning
    # |                        | 2  Fixpunkt
    # |                        | 3  Fixavspenning
    # |                        | 4  Avspenning
    # |                        | 5  Forbigangsledning
    # |                        | 6  Returledning
    # |                        | 7  Fiberoptisk ledning
    # |                        | 8  Mate-/fjernledning
    # |                        | 9  AT-ledning
    # |                        | 10 Jordledning
    # |                        | 11 Snø og is
    # |                        | 12 Vind (fra mast, mot spor)
    # |                        | 13 Vind (fra spor, mot mast)
    # |                        | 14 Vind (parallelt spor)
    #  ------------------------
    #
    #
    # D = forskyvning av mast i kontakttradhøyde FH
    #
    #       D
    #
    #   Indekser:
    #   0   1   2
    #   Dy  Dz  phi
    #  _____________
    # |             | 0  Egenvekt (mast, utligger, ledninger)
    # |             | 1  Kontaktledning
    # |             | 2  Fixpunkt
    # |             | 3  Fixavspenning
    # |             | 4  Avspenning
    # |             | 5  Forbigangsledning
    # |             | 6  Returledning
    # |             | 7  Fiberoptisk ledning
    # |             | 8  Mate-/fjernledning
    # |             | 9  AT-ledning
    # |             | 10 Jordledning
    # |             | 11 Snø og is
    # |             | 12 Vind (fra mast, mot spor)
    # |             | 13 Vind (fra spor, mot mast)
    # |             | 14 Vind (parallelt spor)
    #  -------------



    # Oppretter masteobjekt med brukerdefinert høyde
    master = mast.hent_master(i.h, i.s235, i.materialkoeff)
    # Oppretter systemobjekt med data for ledninger og utliggere
    sys = system.hent_system(i)
    # q_p = klima.beregn_vindkasthastighetstrykk_EC(i.h)
    q_p = i.vindkasthastighetstrykk * 1000  # [N/m^2]
    B1, B2, e_max = geometri.beregn_sikksakk(sys, i)
    a_T, a_T_dot = geometri.beregn_arm(i, B1)

    # FELLES FOR ALLE MASTER
    F_generell = []
    F_generell.extend(laster.beregn(sys, i, a_T, a_T_dot, B1, B2))
    #F_generell.extend(klima.isogsno_last(i, sys, a_T, a_T_dot))

    # Sidekrefter til beregning av utliggerens deformasjonsbidrag
    sidekrefter = []
    for j in F_generell:
        if j.navn == "Sidekraft: Bæreline" or j.navn == "Sidekraft: Kontakttråd"\
                or j.navn == "Sidekraft: Avspenning bæreline" \
                or j.navn == "Sidekraft: Avspenning kontakttråd":
            sidekrefter.append(j.f[2])

    if i.ec3:
        # Beregninger med lastfaktorkombinasjoner ihht. EC3

        F_generell.extend(klima.vindlast_ledninger_EC(i, sys, q_p))

        # Definerer grensetilstander inkl. lastfaktorer for ulike lastfaktorer i EC3
        # g = egenvekt, l = loddavspente, f = fastavspente/fix, k = klima
        bruddgrense = {"Navn": "bruddgrense", "g": [1.0, 1.2], "l": [0.9, 1.2],
                       "f": [0.0, 1.2], "k": [1.5]}
        forskyvning_kl = {"Navn": "forskyvning_kl",
                          "g": [0.0], "l": [0.0], "f": [-0.25, 0.7], "k": [1.0]}
        forskyvning_tot = {"Navn": "forskyvning_tot",
                           "g": [1.0], "l": [1.0], "f": [0.0, 1.0], "k": [1.0]}

        grensetilstander = [bruddgrense, forskyvning_kl, forskyvning_tot]

        # UNIKT FOR HVER MAST
        for mast in master:

            F = []
            F.extend(F_generell)
            F.extend(laster.egenvekt_mast(mast))
            F.extend(klima.vandringskraft(i, sys, mast, B1, B2, a_T, a_T_dot))
            F.extend(klima.vindlast_mast_EC(mast, q_p))

            if mast.navn == "H5":
                for j in F:
                    print(j)

            R = _beregn_reaksjonskrefter(F)
            D = _beregn_deformasjoner(i, sys, mast, F, sidekrefter)


            # Samler laster med lastfaktor g
            gravitasjonslast = [R[0][:], D[0][:]]

            # Samler laster med lastfaktor l
            loddavspente = [R[1][:], D[1][:]]

            # Samler laster med lastfaktor f (f1)
            fix = [numpy.sum(R[2:4][:], axis=0), numpy.sum(D[2:4][:], axis=0)]

            # Samler laster med lastfaktor f (f2)
            fastavspente = [numpy.sum(R[4:8][:], axis=0), numpy.sum(D[4:8][:], axis=0)]

            # Samler laster med lastfaktor f (f3)
            toppmonterte = [numpy.sum(R[8:11][:], axis=0), numpy.sum(D[8:11][:], axis=0)]

            # Faktor k brukes for beregning av klimalaster
            sno = [R[11][:], D[11][:]]
            vind_max = [R[12][:], D[12][:]]  # Vind fra mast, mot spor
            vind_min = [R[13][:], D[13][:]]  # Vind fra spor, mot mast
            vind_par = [R[14][:], D[14][:]]  # Vind parallelt spor

            """Sammenligner alle mulige kombinasjoner av lastfaktorer
            for hver enkelt grensetilstand og lagrer resultat av hver enkelt
            sammenligning i sitt respektive masteobjekt
            """
            for grensetilstand in grensetilstander:
                index = 1
                if grensetilstand["Navn"] == "bruddgrense":
                    index = 0
                for g in grensetilstand["g"]:
                    for l in grensetilstand["l"]:
                        for f1 in grensetilstand["f"]:
                            for f2 in grensetilstand["f"]:
                                for f3 in grensetilstand["f"]:
                                    for k in grensetilstand["k"]:
                                        K = (g * gravitasjonslast[index]
                                            + l * loddavspente[index]
                                            + f1 * fix[index]
                                            + f2 * fastavspente[index]
                                            + f3 * toppmonterte[index])
                                        K1 = K + k * (sno[index] + vind_max[index])
                                        K2 = K + k * (sno[index] + vind_min[index])
                                        K3 = K + k * (sno[index] + vind_par[index])
                                        t1 = tilstand.Tilstand(mast, i, R, K1, 1,
                                                              grensetilstand, F,
                                                              g, l, f1, f2,
                                                              f3, k)
                                        t2 = tilstand.Tilstand(mast, i, R, K2, 2,
                                                               grensetilstand, F,
                                                               g, l, f1, f2,
                                                               f3, k)
                                        t3 = tilstand.Tilstand(mast, i, R, K3, 3,
                                                               grensetilstand, F,
                                                               g, l, f1, f2,
                                                               f3, k)
                                        mast.lagre_tilstand(t1)
                                        mast.lagre_tilstand(t2)
                                        mast.lagre_tilstand(t3)

    else:
        # Beregninger med lasttilfeller fra bransjestandard EN 50119

        F_generell.extend(klima.vindlast_ledninger_NEK(i, sys))

        bruddgrense = {"Navn": "bruddgrense", "G": [1.3], "Q": [1.3]}
        forskyvning_kl = {"Navn": "forskyvning_kl", "G": [0], "Q": [1.0]}
        forskyvning_tot = {"Navn": "forskyvning_tot", "G": [1.0], "Q": [1.0]}

        grensetilstander = [bruddgrense, forskyvning_kl, forskyvning_tot]


        # UNIKT FOR HVER MAST
        for mast in master:

            F = []
            F.extend(F_generell)
            F.extend(laster.egenvekt_mast(mast))
            F.extend(klima.vandringskraft(i, sys, mast, B1, B2, a_T, a_T_dot))
            F.extend(klima.vindlast_mast_NEK(mast))

            R = _beregn_reaksjonskrefter(F)
            D = _beregn_deformasjoner(i, sys, mast, F, sidekrefter)

            # Permanente laster (lastfaktor G)
            permanente = [numpy.sum(R[0:11][:], axis=0), numpy.sum(D[0:11][:], axis=0)]

            # Variable laster (lastfaktor Q)
            sno = [R[11][:], D[11][:]]
            vind_max = [R[12][:], D[12][:]]  # Vind fra mast, mot spor
            vind_min = [R[13][:], D[13][:]]  # Vind fra spor, mot mast
            vind_par = [R[14][:], D[14][:]]  # Vind parallelt sor

            if mast.navn == "H5":
                print("T fra sno = {} kNm".format(sno[0][5]/1000))
                print("T fra vind_1 = {} kNm".format(vind_max[0][5] / 1000))
                print("T fra vind_2 = {} kNm".format(vind_min[0][5] / 1000))
                print("T fra vind_3 = {} kNm".format(vind_par[0][5] / 1000))

            for grensetilstand in grensetilstander:
                G = grensetilstand["G"]
                Q = grensetilstand["Q"]
                index = 1
                if grensetilstand["Navn"] == "bruddgrense":
                    index = 0
                K1 = G * permanente[index] + Q * (sno[index] + vind_max[index])
                K2 = G * permanente[index] + Q * (sno[index] + vind_min[index])
                K3 = G * permanente[index] + Q * (sno[index] + vind_par[index])
                t1 = tilstand.Tilstand(mast, i, R, K1, 1,
                                       grensetilstand, F,
                                       G=G, Q=Q)
                t2 = tilstand.Tilstand(mast, i, R, K2, 2,
                                       grensetilstand, F,
                                       G=G, Q=Q)
                t3 = tilstand.Tilstand(mast, i, R, K3, 3,
                                       grensetilstand, F,
                                       G=G, Q=Q)
                mast.lagre_tilstand(t1)
                mast.lagre_tilstand(t2)
                mast.lagre_tilstand(t3)

    # Sjekker minnebruk (TEST)
    TEST.print_memory_info()

    return master






















