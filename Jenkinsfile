@Library('pcic-pipeline-library')_


node {
    stage('Code Collection') {
        collectCode()
    }

    stage('Testing') {
        def requirements = ['requirements.txt']
        def pytestArgs = '-v tests'
        def options =  [aptPackages: ['libhdf5-serial-dev', 'libnetcdf-dev']]

        parallel "Python 3.6": {
            runPythonTestSuite('crmprtd-python36', requirements, pytestArgs)
        },
        "Python 3.7": {
            runPythonTestSuite('crmprtd-python37', requirements, pytestArgs,
                               options)
        }
    }

    if (isPypiPublishable()) {
        stage('Push to PYPI') {
            publishPythonPackage('crmprtd-python36', 'PCIC_PYPI_CREDS')
        }
    }

    stage('Clean Workspace') {
        cleanWs()
    }
}
