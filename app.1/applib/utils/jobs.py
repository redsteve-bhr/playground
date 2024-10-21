# -*- coding: utf-8 -*-
#
# Copyright 2011 Grosvenor Technology
#

"""
:mod:`jobs` --- Jobs and Job Queues 
===================================

.. versionadded:: 1.5

Executing jobs while showing a wait screen is a very common task in 
applications. However, interrupting and cancelling these jobs can 
sometimes be very difficult. 
Jobs and job queues attempt to provide the necessary building blocks 
to make these tasks easier to implement. 

Simple job::

    class MyJob(Job):
    
        def execute(self):
            # This "fake" job will only wait 2 to 10 seconds 
            time.sleep(random.randint(2, 10))
    

Example with :func:`itg.waitbox`::

    queue = JobQueue()
    job = MyJob()
    queue.addJob(job)
    itg.waitbox(_('Executing job, please wait...'), job.wait) 
    
The example above will show the waitbox dialog as long as the job is executed. The 
following example will add a timeout and cancel button.

Example with :func:`itg.waitbox`, timeout and cancel::

    timeout = 5
    queue = JobQueue()
    job = MyJob()
    queue.addJob(job)
    itg.waitbox(_('Executing job, please wait...'), job.wait, (timeout,), job.cancel) 

In the example above, the waitbox dialog will be shown as long as the job takes or until the
timeout is reached or the cancel button is pressed. Please note, that in case of a timeout
or cancel only :meth:`Job.wait` is interrupted not :meth:`Job.execute`.
However, when the state of a job changes from **RUNNING** to **CANCELLED** or **TIMEDOUT**
:meth:`Job.stop` is executed. This method can be overwritten to try and interrupt :meth:`Job.execute`.

Example with :meth:`Job.stop`::

    class MyJob(Job):
    
        def __init__(self):
            super(MyJob, self).__init__()
            self._event = threading.Event()
    
        def execute(self):
            # This "fake" job will just wait 30 seconds, but be interruptable
            self._event.wait(30)
            
        def stop(self):
            # interrupt execute function
            self._event.set()
    

It is good practice to re-use a job queue for the same kind of jobs (e.g. online information requests).
:class:`JobQueue` will execute each :class:`Job` in the queue in the order they were added. As mentioned
above, cancelling a job or timing out in :meth:`Job.wait` will not automatically interrupt :meth:`Job.execute`
and therefore not start the execution of the next job! 
A :class:`JobQueue` should be checked for the number of pending jobs, if used for something like real time 
information requests.

Example with checking current queue status::

    queue = getRealTimeInfoQueue()
    if (queue.isBusy()):
        itg.msgbox(itg.MB_OK, _('Real time information are currently not possible, please try later...'))
    else:
        job = GetRealTimeInfoJob()
        timeout = 10
        queue.addJob(job)
        itg.waitbox(_('Requesting information, please wait...'), job.wait, (timeout,), job.cancel)
        if (job.hasFinished()):
            itg.msgbox(itg.MB_OK, _('Your information is: %s') % job.getInfo())
        elif (job.hasFailed()):
            itg.msgbox(itg.MB_OK, _('Failed to get information: %s') % job.getFailedReason())
        elif (job.hasTimedout()):
            itg.msgbox(itg.MB_OK, _('Failed to get information in time'))


Threading considerations
------------------------

Each :class:`JobQueue` implements its own thread, which means that in the examples above 2 background
threads were active. The foreground thread was busy with handling :class:`itg.waitbox` while :meth:`Job.wait`
was executed in the waitbox background thread and :meth:`Job.execute` was executed in the job queue thread.
:meth:`Job.stop` is executed in the same thread as :meth:`Job.wait`. 

Classes
-------

        
"""

import threading
import log
import time

class Job(object):
    """ The Job class 
    
    .. versionadded:: 1.5
    
    """
    
    INACTIVE    = 0
    WAITING     = 1
    RUNNING     = 2
    CANCELLED   = 3
    TIMEDOUT    = 4
    FAILED      = 5
    FINISHED    = 6
    
    def __init__(self, name=None):
        self._condition = threading.Condition()
        self._name  = name if name != None else self.__class__.__name__
        self._state = Job.INACTIVE
        self._failedReason = None
    
    def getName(self):
        """ Return name of job. """
        return self._name
    
    def getState(self):
        return self._state

    def _setState(self, state):
        with self._condition:
            self._state = state
            self._condition.notifyAll()
    
    def execute(self):
        """ This method must be implemented by the derived class to actually
        execute the job (background task)."""
        pass
    
    def stop(self):
        """ This method may be implemented to try and stop the job executed
        by :meth:`execute`. :meth:`stop` is called automatically when the 
        state of the job is changed to **CANCELLED** or **TIMEDOUT** and should 
        not take much time to execute.
        """
        pass

    def wait(self, timeout=None):
        """ Wait up to *timeout* seconds until job has finished, failed or was
        cancelled. """
        log.dbg('Waiting for %s (timeout=%s)' % (self.getName(), timeout))
        maxTimeout = timeout
        with self._condition:
            if (timeout != None):
                endTime = time.time() + timeout            
            while (self._state in (Job.WAITING, Job.RUNNING)):
                if (timeout!=None and timeout <= 0):
                    self._state = Job.TIMEDOUT
                    break
                self._condition.wait(timeout)
                if (timeout != None): # Recalculate remaining time
                    timeout = endTime - time.time()
                    if (timeout > maxTimeout):
                        timeout = 5

    def cancel(self, *params):
        """ Cancel job. """
        with self._condition:
            self._setState(Job.CANCELLED)
            self.stop()

    def setWaiting(self):
        self._setState(Job.WAITING)
                
    def setRunning(self):
        self._setState(Job.RUNNING)        
    
    def setFinished(self):
        self._setState(Job.FINISHED)

    def setFailed(self, reason):
        with self._condition:
            self._failedReason = reason
            self._setState(Job.FAILED)     
    
    def wasCancelled(self):
        """ Return **True** if job was cancelled by user (:meth:`cancel`). """
        return (self._state == Job.CANCELLED)
    
    def hasFinished(self):
        """ Return **True** if job finished successfully. """
        return (self._state == Job.FINISHED)
    
    def hasFailed(self):
        """ Return **True** if job failed (:meth:`execute` raised an exception). """
        return (self._state == Job.FAILED)   
    
    def hasTimedout(self):
        """ Return **True** if the job timed out. """
        return (self._state == Job.TIMEDOUT)

    def isInProgress(self):
        """ Return **True** if job has not finished executing. 
        
        .. versionadded:: 3.0
        
        """
        return (self._state in (Job.WAITING, Job.RUNNING))

    def getFailedReason(self):
        """ Return failed reason. 
        
        .. versionadded:: 1.6
        
        """
        return self._failedReason


class JobQueue(threading.Thread):
    """ A JobQueue is a thread which executes jobs from a queue. It is possible and sometimes advisable to
    have many different job queues in an application (e.g. different ones for online clockings and online
    requests). However, it is bad practice to create a new job queue for every job.
    
    .. versionadded:: 1.5
    
    """

    def __init__(self, name):
        super(JobQueue, self).__init__()
        self._name  = name if name != None else self.__class__.__name__
        self._running = True
        self._queue = []
        self._condition = threading.Condition()
    
    def getName(self):
        """ Return name of job queue. """
        return self._name

    def getNumberOfJobs(self):
        """ Return number of jobs in queue. """
        return len(self._queue)
    
    def isBusy(self):
        """ Return **True** is queue is not empty. """
        return (len(self._queue) > 0)
    
    def addJob(self, job):
        """ Add a job into queue. """
        if (not self.isAlive()):
            self.start()
        log.dbg('Adding job %s into %s ...' % (job.getName(), self.getName()))
        with self._condition:
            self._queue.append(job)
            job.setWaiting()
            self._condition.notifyAll()
    
    def addJobAndWait(self, job, timeout=None):
        """ Add *job* into queue and wait up to *timeout* seconds until job is executed. 
        
        .. note::
            This is the same as::
                
                jobQueue.add(job)
                job.wait(timeout)
        
        """
        self.addJob(job)
        job.wait(timeout)

    def stop(self, timeout=5):
        """ Stop job queue thread. """
        log.dbg('Stopping %s' % self.getName())
        with self._condition:
            self._running = False
            self._condition.notifyAll()
        if (self.isAlive()):
            self.join(timeout)
        log.dbg('%s stopped' % self.getName())
    
    def run(self):
        log.dbg('%s started' % self.getName())
        while self._running:
            job = None
            with self._condition:
                while not self._queue and self._running:
                    log.dbg('Waiting for jobs')
                    self._condition.wait()
                if (self._queue and self._running):
                    job = self._queue[0]
            if (job):
                try:
                    job.setRunning()
                    job.execute()
                    job.setFinished()
                except Exception as e:
                    log.err('Job %s failed: %s' % (job.getName(), e))
                    job.setFailed(str(e))                    
                finally:
                    with self._condition:
                        log.dbg('Removing job %s from %s' % (job.getName(), self.getName()))
                        self._queue.remove(job)
        log.dbg('%s is stopping...' % self.getName())

