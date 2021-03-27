#! /usr/bin/python
import os
import sys
import rospkg
import subprocess
import resource
import cv2
from fiducial_svg import checkCmd, genFiducialwithBorder

import json

svgScale = 22.0/18.0    

def genMarker(x, q, fid, dicno, pack_id):
    pathToDict = os.path.join(markersPath, dicno)
    pathToMarker = os.path.join(pathToDict, "%05d.png" % x)
    img = cv2.imread(pathToMarker)

    if img is None:
        sys.exit("Marker image not found. This means that you have not provided the correct path to the downloaded STag markers. Aborting.")

    borderSize = 100
    croppedSize = 800
    croppedImg = img[borderSize: borderSize+croppedSize, borderSize: borderSize+croppedSize]

    cv2.imwrite("/tmp/marker%d.png" % x, croppedImg)

    svg = genFiducialwithBorder(x, q - 1, fid, pack_id + 1, fid_len=180.0*180.0/220.0)
    
    if svgScale == 1.0:
        cairo = subprocess.Popen(
            ('cairosvg', '-f', 'pdf', '-o', '/tmp/marker%d-%d.pdf' % (x, pack_id), '/dev/stdin'), stdin=subprocess.PIPE)
    else:
        # If you get an error which says that "-s" option is not recognized, download newer version of cairosvg with "$ pip3 install cairosvg".
        cairo = subprocess.Popen(
            ('cairosvg', '-f', 'pdf', '-s', str(svgScale), '-o', '/tmp/marker%d-%d.pdf' % (x, pack_id), '/dev/stdin'), stdin=subprocess.PIPE)   

    cairo.communicate(input=svg)
    os.remove("/tmp/marker%d.png" % x)


if __name__ == '__main__':

    limits = resource.getrlimit(resource.RLIMIT_NOFILE)
    if limits[1] < 10000:
        print(
            "Aborting due to resource usage limitation, call 'sudo ./ulimit_setup' before running the script again!")
        exit()

    checkCmd("pdfunite", "poppler-utils")
    checkCmd("cairosvg", "python-cairosvg")
    print("	---- Fiducial Marker Generator by ----						 \n \
             _   _ _     _             _ _               ____       _           _   _            \n \
            | | | | |__ (_) __ _ _   _(_) |_ _   _      |  _ \ ___ | |__   ___ | |_(_) ___  ___  \n \
            | | | | '_ \| |/ _` | | | | | __| | | |_____| |_) / _ \| '_ \ / _ \| __| |/ __|/ __| \n \
            | |_| | |_) | | (_| | |_| | | |_| |_| |_____|  _ < (_) | |_) | (_) | |_| | (__ \__ \ \n \
             \___/|_.__/|_|\__, |\__,_|_|\__|\__, |     |_| \_\___/|_.__/ \___/ \__|_|\___||___/ \n \
                              |_|            |___/						")

    dict_info = {
        "HD11": 22309,
        "HD13": 2884,
        "HD15": 766,
        "HD17": 166,
        "HD19": 38,
        "HD21": 12,
        "HD23": 6
    }

    print("Available dictionaries:")
    for key, value in dict_info.items():
        print("ID: %s - SIZE: %d" % (key, value))


    while True:
        try:
            markersPath = str(raw_input("Enter the absolute path to the downloaded STag markers: --> "))
            if not os.path.isdir(markersPath):
                print("This path does not exist - try again.")
                continue
        except (ValueError, NameError, SyntaxError):
            print("Sorry, your input was wrong.")
            continue
        else:
            break

    while True:
        try:
            dicno = raw_input("Enter the STag dictionary ID: --> ")
            
            if str(dicno) not in dict_info.keys():
                print("Wrong STag Dictionary ID - try again.")
                continue
        except (ValueError, NameError, SyntaxError):
            print("Sorry, your input was wrong.")
            continue
        else:
            break

    while True:
        try:
            packs_sizes = [int(size)
                           for size in raw_input("Enter the fiducials packs sizes - example: 100 100 200 200 200 199 (The sum must not exceed the STag dictionary size): --> ").split()]

            if sum(packs_sizes) > dict_info[dicno]:
                print("STag dictionary size exceeded - try again.")
                continue
        except (ValueError, NameError, SyntaxError):
            print("Sorry, your input was wrong.")
            continue
        else:
            break

    while True:
        try:
            percentages = [float(percent)
                           for percent in raw_input("Enter the amount of fiducials in percentages (percentages must sum up to 1.0) in sequence TURN, STOP, BIDIRECTIONAL, GO - example: 0.1 0.2 0.3 0.4: --> ").split()]
            if (len(percentages) != 4) or (sum(percentages) != 1.0):
                print("Sorry, your input was wrong.")
                continue
        except (ValueError, NameError, SyntaxError):
            print("Sorry, your input was wrong.")
            continue
        else:
            break

    while True:
        try:
            outdir = raw_input(
                "Enter the relative path to the directory (where you want to save the .pdf files of generated fiducial packs): --> ")
            if not (os.path.exists(os.path.join(os.getcwd(), outdir))):
                print("Sorry, the directory does not exist - try again.")
                continue
        except (ValueError, NameError, SyntaxError):
            print("Sorry, your input was wrong.")
            continue
        else:
            break

    fiducials = {
        "TURN": {
            "percent": percentages[0],
            "fixed_range": range(1000, 1999),
            "ids": []
        },
        "STOP": {
            "percent": percentages[1],
            "fixed_range": range(2000, 2999),
            "ids": []
        },
        "BIDIR": {
            "percent": percentages[2],
            "fixed_range": range(3000, 3999),
            "ids": []
        },
        "GO": {
            "percent": percentages[3],
            "fixed_range": range(4000, 9999),
            "ids": []
        },
    }

    i = 1
    pdfs = []
    packages_info = []
    for pack_id, pack_size in enumerate(packs_sizes):
        pdfs.append([pack_id])
        packages_info.append({'ranges': {}, 'id_to_number': {}})
        for fiducial in fiducials:
            fiducials[fiducial]["ids"].append([pack_id])

            fid_range = fiducials[fiducial]["fixed_range"]
            packages_info[pack_id]['ranges'][fiducial] = (fid_range[0], fid_range[-1])

            size = int(fiducials[fiducial]["percent"] * pack_size)
            for _ in range(size):
                fiducials[fiducial]["ids"][pack_id].append(i)
                pdfs[pack_id].append(
                    ("/tmp/marker%d-%d.pdf") % (i, pack_id))
                i += 1

    j = 0
    for fid in fiducials:
        for i in range(len(fiducials[fid]["ids"])):
            for x, q in zip(fiducials[fid]["ids"][i], fiducials[fid]["fixed_range"]):
                if x != fiducials[fid]["ids"][i][0]:
                    packages_info[i]['id_to_number'][x] = q - 1
                    genMarker(x, q, fid, dicno, fiducials[fid]["ids"][i][0])
                    sys.stdout.write("Already generated: %s\r" % j)
                    sys.stdout.flush()
                    j += 1

    for i, pdf in enumerate(pdfs):
        pdf.pop(0)
        os.system("pdfunite %s %s" %
                  (" ".join(pdf), os.path.join(os.getcwd(), outdir, "pack-%s.pdf" % str(i + 1))))
        with open("pack-%s-info.json" % str(i + 1), 'w') as f:
            json.dump(packages_info[i], f)
        for f in pdf:
            try:
                os.remove(f)
            except OSError as e:
                print(e)

    print("Pdf files are stored in %s" % os.path.join(os.getcwd(), outdir))
