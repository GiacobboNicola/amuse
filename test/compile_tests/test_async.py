from amuse.support.interface import InCodeComponentImplementation

from amuse.test.amusetest import TestWithMPI
from amuse.support import exceptions
from amuse.support import options

import os
import time
from amuse.units import nbody_system
from amuse.units import units
from amuse import datamodel
from amuse.rfi.tools import create_c
from amuse.rfi import channel
from amuse.rfi.core import *

import test_c_implementation

from amuse.test import compile_tools


codestring=test_c_implementation.codestring+"""
#include <unistd.h>

int do_sleep(int in) {
    sleep(in);
    return 0;
}

"""

class ForTestingInterface(test_c_implementation.ForTestingInterface):
    @legacy_function
    def do_sleep():
        function = LegacyFunctionSpecification()
        function.addParameter('int_in', dtype='int32', direction=function.IN)
        function.result_type = 'int32'
        return function 

class ForTesting(InCodeComponentImplementation):
    
    def __init__(self, exefile, **options):
        InCodeComponentImplementation.__init__(self, ForTestingInterface(exefile, **options), **options)

class TestASync(TestWithMPI):

    def setUp(self):
        super(TestASync, self).setUp()
        print "building...",
        self.check_can_compile_modules()
        try:
            self.exefile = compile_tools.build_worker(codestring, self.get_path_to_results(), ForTestingInterface)
        except Exception as ex:
            print ex
            raise
        print "done"
        
    def test1(self):
        instance = ForTestingInterface(self.exefile)
        int_out, error = instance.echo_int(10)
        instance.stop()
        self.assertEquals(int_out, 10)
        self.assertEquals(error, 0)

    def test2(self):
        instance = ForTestingInterface(self.exefile)
        request = instance.echo_int.async(10)
        self.assertEqual(request, instance.async_request)
        request.wait()
        int_out,error=request.result()
        self.assertEquals(int_out, 10)
        self.assertEquals(error, 0)
        instance.stop()

    def test3(self):
        instance = ForTestingInterface(self.exefile)
        request1 = instance.do_sleep.async(1)
        request2 = instance.echo_int.async(10)
        self.assertEqual(request2, instance.async_request)
        request2.wait()
        int_out,error=request2.result()
        self.assertEquals(int_out, 10)
        self.assertEquals(error, 0)
        instance.stop()

    def test4(self):
        instance = ForTesting(self.exefile)
        request1 = instance.do_sleep(1, async=True)
        request2 = instance.echo_int(10, async=True)
        self.assertEqual(request2, instance.async_request)
        instance.async_request.wait()
        int_out=request2.result()
        self.assertEquals(int_out, 10)
        instance.stop()

    def test5(self):
        instance = ForTesting(self.exefile)
        instance.do_sleep(1, async=True)
        requests=[]
        for x in range(10):
            requests.append(instance.echo_int(x, async=True))
        instance.async_request.wait()
        for i,x in enumerate(requests):
            self.assertEquals(x.result(), i)
        instance.stop()

    def test6(self):
        instance = ForTesting(self.exefile)
        requests=[]
        for x in range(10):
            requests.append(instance.echo_int(x, async=True))
        instance.async_request.wait()
        for i,x in enumerate(requests):
            self.assertEquals(x.result(), i)
        instance.stop()

    def test7(self):
        instance1 = ForTesting(self.exefile)
        instance2 = ForTesting(self.exefile)
        t1=time.time()

        requests=[]
        for x in range(10):
            requests.append([instance1.echo_int(x, async=True),x])
        for x in range(10):
            requests.append([instance2.echo_int(x, async=True),x])

        instance1.do_sleep(1, async=True)
        instance2.do_sleep(1, async=True)

        pool=instance1.async_request.join(instance2.async_request)
        pool.waitall()
        t2=time.time()

        for x in requests:
            self.assertEquals(x[0].result(), x[1])
        instance1.stop()
        instance2.stop()
        self.assertTrue(t2-t1 < 2.)

    def test8(self):
        from threading import Thread
        instance1 = ForTesting(self.exefile)
        instance2 = ForTesting(self.exefile)
        t1=time.time()

        requests=[]
        for x in range(10):
            requests.append([instance1.echo_int(x, async=True),x])
        for x in range(10):
            requests.append([instance2.echo_int(x, async=True),x])

        instance1.do_sleep(1, async=True)
        instance2.do_sleep(1, async=True)

        pool=instance1.async_request.join(instance2.async_request)
        
        thread=Thread(target=pool.waitall)
        thread.start()
        time.sleep(1)
        thread.join()
        
        self.assertTrue(pool)
        
        t2=time.time()

        for x in requests:
            self.assertEquals(x[0].result(), x[1])
        instance1.stop()
        instance2.stop()
        self.assertTrue(t2-t1 < 2.)

