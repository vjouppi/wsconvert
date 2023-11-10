#!/usr/bin/python3

import sys
import argparse

def specialchars(x):
    return {
        0x0D : 0,    # skip newline handling
        0x0A : 0,
        0x8D : 0,
        0x8A : 0,
        0x19 : 0x2A, #italic
        0x99 : 0x2A, #italic end
        0x13 : 0x2A, #underline->italic
        0x93 : 0x2A, #underline->italic end
        0x02 : 0x2A, #bold
        0x82 : 0x2A, #bold end
        0x14 : 0x5E, #superscript
        0x94 : 0x5E, #superscript end
        0x16 : 0x7E, #subscript
        0x96 : 0x7E, #subscript end
        0x18 : 0x7E, #strikethrough
        0x98 : 0x7E  #strikethrough end
    }.get(x,0)

def handleblock(block):
    # implement here the handling of the blocks
    # block[0] is the length of the block (int)
    # block[2] is the command
    if block[2] == 0x03: # footer
        footerdata = converttext(block[20:]).replace(b'\n',b'')
        return b'^['+footerdata+b']'
    elif block[2] == 0x09: # TAB
        return b'    '
    elif block[2] == 0x11: # paragraph style
        if block[3] == 0x02: # header
            return b'## '
        elif block[3]== 0x05: #title
            return b'# '
    return b''

def converttext(data):
    counter=-1
    newline = False

    if data[0] == 0x2E: #begins with a dotline
        linetype = 1
    else:
        linetype = 0

    outdata=bytearray()
    while counter<len(data)-1:
        counter+=1
        # End of file character
        if data[counter] == 0x1A:
            break
        # Extended character
        elif data[counter]==0x1B:
            if linetype == 0: # we don't care about extended chars in dotlines
                outdata.append(data[counter+1])
            counter += 2
        # Symmetrical sequence: 1Dh special character
        elif data[counter]==0x1D:
            jump=int.from_bytes(data[counter+1:counter+2],byteorder='little')
            if not args.textmode:
                outdata += (handleblock(data[counter+1:counter+jump]))
            counter += jump+2
        elif data[counter]<0x20:    # special formatting characters
            if data[counter] == 0x0D and not newline:
                #outdata += b'\x0D\x0A\x0D\x0A'
                if linetype == 0: # dotlines should be eaten, not blank
                    outdata += b'\x0D\x0A'
                newline = True
                linetype = 0
            if not args.textmode:   # handle formatting for markdown
                c=specialchars(data[counter])
                if not c == 0:
                    outdata.append(c)
                if data[counter] == 0x02 or data[counter] == 0x18:
                    outdata.append(c)   # duplicating some characters ** and ~~
        elif data[counter]<0x80:    # other characters
            if newline:
                newline = False
                if data[counter] == 0x2E: # dotline
                    linetype = 1
                #if data[counter] == 0x2D: # special line (list)
                #    outdata.pop()
            if linetype != 1: # we are in a dotline => ignore it
                outdata.append(data[counter])
        elif specialchars(data[counter]):
            if not args.textmode:
                c=specialchars(data[counter])
                if not c == 0:
                    outdata.append(c)
                if data[counter] == 0x82 or data[counter] == 0x98:
                    outdata.append(c)   # duplicating some characters ** and ~~
        elif data[counter]==0x9B: # sometimes extended characters are esc + 0x80
            outdata.append(data[counter+1])
            counter += 2
        elif data[counter]==0x8D or data[counter]==0x8A:
            pass
        elif data[counter]>=0x80:   # kill 8th bit for ending characters
            outdata.append(data[counter]-0x80)
    return outdata

print("Basic WordStar to Markdown converter")
print("====================================")
# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("ws_file",help="the WordStar file to convert")
parser.add_argument("-o","--output", help="output file name")
parser.add_argument("-t","--textmode", help="output to unformatted (text) file",
                    action="store_true")
args = parser.parse_args()

if args.output:
    outputfile = args.output
else:
    extension = ".txt" if args.textmode else ".md"
    pp=args.ws_file.find('.')
    outfilename=args.ws_file[0:pp]+extension

#Read file
print("Reading "+args.ws_file)
with open(args.ws_file,"rb") as infile:
    data=infile.read()

# Let's go through the file for some cleanup...
print("Converting...");
outdata = converttext(data)

# Now decode the extended ascii data...
outstring=outdata.decode("cp437")
with open(outputfile,"wt") as outfile:
    outfile.write(outstring)
print("Conversion ready, "+outputfile+" written!")
