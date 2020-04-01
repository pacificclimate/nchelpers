@Library('pcic-pipeline-library')_


node {
    stage('Code Collection') {
        collectCode()
    }

    stage('Testing') {
        def requirements = ['requirements.txt']
        def pytestArgs = '-v tests'
        def options = [
            aptPackages: ['libhdf5-serial-dev', 'libnetcdf-dev', 'git']
        ]

        parallel "Python 3.6": {
            runPythonTestSuite('python:3.6', requirements, pytestArgs)
        },
        "Python 3.7": {
            runPythonTestSuite('python:3.7', requirements, pytestArgs,
                               options)
        }
    }

    stage('Clean Workspace') {
        cleanWs()
    }

    stage('Code Collection') {
        collectCode()
    }

    if (isPypiPublishable()) {
        stage('Push to PYPI') {
            publishPythonPackage('pcic/crmprtd-test-env:python-3.6', 'PCIC_PYPI_CREDS')
        }
    }

    stage('Clean Workspace') {
        cleanWs()
    }
}
