#! /usr/bin/python
#------------------------------------------------------------------------------

import os
import sys
import subprocess
import re
import argparse
import tempfile
#------------------------------------------------------------------------------

mypath = '.'


def testCompare(tmpFileName, stdout, expectFile, f, args):
    expect = open(expectFile, 'r').read()

    if args['docker']:
        expect = re.sub( r'instantiated from: .*?.cpp:', r'instantiated from: x.cpp:', expect)

    if stdout != expect:
        print '[FAILED] %s' %(f)
        cmd = ['/usr/bin/diff', expectFile, tmpFileName]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        print stdout
    else:
        print '[PASSED] %s' %(f)
        return True

    return False
#------------------------------------------------------------------------------

def testCompile(tmpFileName, f, args, fileName):
    cmd = [args['cxx'], '-std=c++1z', '-c', tmpFileName]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    compileErrorFile = os.path.join(mypath, fileName + '.cerr')
    if 0 != p.returncode:


        if os.path.isfile(compileErrorFile):
            ce = open(compileErrorFile, 'r').read()
            stderr = stderr.replace(tmpFileName, '.tmp.cpp')

            if ce == stderr:
                print '[PASSED] Compile: %s' %(f)
                return True

        compileErrorFile = os.path.join(mypath, fileName + '.ccerr')
        if os.path.isfile(compileErrorFile):
                ce = open(compileErrorFile, 'r').read()
                stderr = stderr.replace(tmpFileName, '.tmp.cpp')

                if ce == stderr:
                    print '[PASSED] Compile: %s' %(f)
                    return True

        print '[ERROR] Compile failed: %s' %(f)
        print stderr
        ret = 1
    else:
        if os.path.isfile(compileErrorFile):
            print 'unused file: %s' %(compileErrorFile)

        print '[PASSED] Compile: %s' %(f)
        return True

    return False
#------------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description='Description of your program')
    parser.add_argument('--insights',       help='C++ Insights binary',  required=True)
    parser.add_argument('--cxx',            help='C++ compiler to used', default='/usr/local/clang-current/bin/clang++')
    parser.add_argument('--docker',         help='Run tests in docker container', action='store_true')
    parser.add_argument('--docker-image',   help='Docker image name', default='cppinsights-runtime')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = vars(parser.parse_args())

    insightsPath  = args['insights']
    remainingArgs = args['args']

    if 0 == len(remainingArgs):
        cppFiles = [f for f in os.listdir(mypath) if (os.path.isfile(os.path.join(mypath, f)) and f.endswith('.cpp'))]
    else:
        cppFiles = remainingArgs

    if args['docker']:
        print 'Running tests in docker'

    filesPassed     = 0
    missingExpected = 0
    ret             = 0
    for f in sorted(cppFiles):
        fileName   = os.path.splitext(f)[0]
        expectFile = os.path.join(mypath, fileName + '.expect')

        if not os.path.isfile(expectFile):
            print 'Missing expect for: %s' %(f)
            missingExpected += 1
            continue

        if args['docker']:
                data = open(f, 'r').read()
                cmd = ['docker', 'run', '-i', args['docker_image'], insightsPath, '-stdin', 'x.cpp', '--', '-std=c++1z', '-isystem/usr/include/c++/v1/']
                p   = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate(input=data)
        else:
                cmd = [insightsPath, f, '--', '-std=c++1z', '-isystem/usr/local/clang-current/include/c++/v1/', '-isystem/usr/local/clang-current/lib/clang/7.0.0/include']
                p   = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()

        if 0 != p.returncode:
            compileErrorFile = os.path.join(mypath, fileName + '.cerr')
            if os.path.isfile(compileErrorFile):
                ce = open(compileErrorFile, 'r').read()

                if ce == stderr:
                    print '[PASSED] Compile: %s' %(f)
                    filesPassed += 1
                    continue
                else:
                    print '[ERROR] Compile: %s' %(f)
                    ret = 1


            print 'Insight crashed for: %s with: %d' %(f, p.returncode)
            print stderr

            continue

        fd, tmpFileName = tempfile.mkstemp('.cpp')
        try:
            with os.fdopen(fd, 'w') as tmp:
                # do stuff with temp file
                tmp.write(stdout)

            equal = testCompare(tmpFileName, stdout, expectFile, f, args)

            if testCompile(tmpFileName, f, args, fileName) and equal:
                filesPassed += 1

        finally:
            os.remove(tmpFileName)



    expectedToPass = len(cppFiles)-missingExpected
    print '-----------------------------------------------------------------'
    print 'Tests passed: %d/%d' %(filesPassed, expectedToPass)

#    return expectedToPass != filesPassed # note bash expects 0 for ok
    return 0
#------------------------------------------------------------------------------


sys.exit(main())
#------------------------------------------------------------------------------

