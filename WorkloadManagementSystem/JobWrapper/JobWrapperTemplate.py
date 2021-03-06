import sys
sys.path.insert( 0, "@SITEPYTHON@" )
from DIRAC.Core.Base import Script
Script.parseCommandLine()
#######################################################################################################################
# $Id$
# Generated by JobAgent version: @SIGNATURE@ for Job @JOBID@ on @DATESTRING@.
#######################################################################################################################

from DIRAC.WorkloadManagementSystem.JobWrapper.JobWrapper   import JobWrapper, rescheduleFailedJob
from DIRAC.WorkloadManagementSystem.Client.JobReport        import JobReport

from DIRAC                                                  import gLogger

import os

os.umask( 022 )

class JobWrapperError( Exception ):
  def __init__( self, value ):
    self.value = value
  def __str__( self ):
    return str( self.value )

gJobReport = None

def execute ( arguments ):

  global gJobReport

  jobID = arguments['Job']['JobID']
  os.environ['JOBID'] = jobID
  jobID = int( jobID )
  # Fix in the environment to get a reasonable performance from dCache,
  # until we move to a new version of root
#  os.environ['DCACHE_RAHEAD'] = str(1)
#  os.environ['DCACHE_RA_BUFFER'] = str(50*1024)

  if arguments.has_key( 'WorkingDirectory' ):
    wdir = os.path.expandvars( arguments['WorkingDirectory'] )
    if os.path.isdir( wdir ):
      os.chdir( wdir )
    else:
      try:
        os.makedirs( wdir )
        if os.path.isdir( wdir ):
          os.chdir( wdir )
      except Exception:
        gLogger.exception( 'JobWrapperTemplate could not create working directory' )
        rescheduleResult = rescheduleFailedJob( jobID, 'Could Not Create Working Directory' )
        return 1

  #root = arguments['CE']['Root']
  gJobReport = JobReport( jobID, 'JobWrapper' )

  try:
    job = JobWrapper( jobID, gJobReport )
    job.initialize( arguments )
  except Exception:
    gLogger.exception( 'JobWrapper failed the initialization phase' )
    rescheduleResult = rescheduleFailedJob( jobID, 'Job Wrapper Initialization', gJobReport )
    job.sendWMSAccounting( rescheduleResult, 'Job Wrapper Initialization' )
    return 1

  if arguments['Job'].has_key( 'InputSandbox' ):
    gJobReport.commit()
    try:
      result = job.transferInputSandbox( arguments['Job']['InputSandbox'] )
      if not result['OK']:
        gLogger.warn( result['Message'] )
        raise JobWrapperError( result['Message'] )
    except Exception:
      gLogger.exception( 'JobWrapper failed to download input sandbox' )
      rescheduleResult = rescheduleFailedJob( jobID, 'Input Sandbox Download', gJobReport )
      job.sendWMSAccounting( rescheduleResult, 'Input Sandbox Download' )
      return 1
  else:
    gLogger.verbose( 'Job has no InputSandbox requirement' )

  gJobReport.commit()

  if arguments['Job'].has_key( 'InputData' ):
    if arguments['Job']['InputData']:
      try:
        result = job.resolveInputData()
        if not result['OK']:
          gLogger.warn( result['Message'] )
          raise JobWrapperError( result['Message'] )
      except Exception, x:
        gLogger.exception( 'JobWrapper failed to resolve input data' )
        rescheduleResult = rescheduleFailedJob( jobID, 'Input Data Resolution', gJobReport )
        job.sendWMSAccounting( rescheduleResult, 'Input Data Resolution' )
        return 1
    else:
      gLogger.verbose( 'Job has a null InputData requirement:' )
      gLogger.verbose( arguments )
  else:
    gLogger.verbose( 'Job has no InputData requirement' )

  gJobReport.commit()

  try:
    result = job.execute( arguments )
    if not result['OK']:
      gLogger.error( result['Message'] )
      raise JobWrapperError( result['Message'] )
  except Exception, x:
    if str( x ) == '0':
      gLogger.verbose( 'JobWrapper exited with status=0 after execution' )
    else:
      gLogger.exception( 'Job failed in execution phase' )
      gJobReport.setJobParameter( 'Error Message', str( x ), sendFlag = False )
      gJobReport.setJobStatus( 'Failed', 'Exception During Execution', sendFlag = False )
      job.sendFailoverRequest( 'Failed', 'Exception During Execution' )
      return 1

  if arguments['Job'].has_key( 'OutputSandbox' ) or arguments['Job'].has_key( 'OutputData' ):
    try:
      result = job.processJobOutputs( arguments )
      if not result['OK']:
        gLogger.warn( result['Message'] )
        raise JobWrapperError( result['Message'] )
    except Exception, x:
      gLogger.exception( 'JobWrapper failed to process output files' )
      gJobReport.setJobParameter( 'Error Message', str( x ), sendFlag = False )
      gJobReport.setJobStatus( 'Failed', 'Uploading Job Outputs', sendFlag = False )
      job.sendFailoverRequest( 'Failed', 'Uploading Job Outputs' )
      return 2
  else:
    gLogger.verbose( 'Job has no OutputData or OutputSandbox requirement' )

  try:
    # Failed jobs will return 1 / successful jobs will return 0
    return job.finalize( arguments )
  except Exception:
    gLogger.exception( 'JobWrapper failed the finalization phase' )
    return 2

###################### Note ##############################
# The below arguments are automatically generated by the #
# JobAgent, do not edit them.                            #
##########################################################
ret = -3
try:
  jobArgs = eval( """@JOBARGS@""" )
  ret = execute( jobArgs )
  gJobReport.commit()
except Exception:
  try:
    gLogger.exception()
    gJobReport.commit()
    ret = -1
  except Exception:
    gLogger.exception()
    ret = -2

sys.exit( ret )
