pipeline {
    agent any
    
    environment {
        ANSIBLE_HOST = credentials('ansible-control-host')
        ANSIBLE_USER = 'ubuntu'
        ANSIBLE_WORKDIR = '/opt/ansible'
    }
    
    stages {
        stage('Test Connection') {
            steps {
                echo 'Testing connection to Ansible Control Node...'
                
                sshagent(credentials: ['ansible-control-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                            \${ANSIBLE_USER}@\${ANSIBLE_HOST} '
                            echo "Connection successful!"
                            echo "Current directory: \$(pwd)"
                            echo "User: \$(whoami)"
                            echo "Date: \$(date)"
                            
                            # Check if Ansible is installed
                            if command -v ansible &> /dev/null; then
                                echo "Ansible version:"
                                ansible --version
                            else
                                echo "Ansible is not installed"
                            fi
                            
                            # Check Python3
                            python3 --version
                            
                            # Check working directory
                            ls -la ${ANSIBLE_WORKDIR} || echo "Ansible working directory not found"
                        '
                    """
                }
            }
        }
        
        stage('Test Ansible Inventory') {
            steps {
                echo 'Testing Ansible inventory configuration...'
                
                sshagent(credentials: ['ansible-control-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                            \${ANSIBLE_USER}@\${ANSIBLE_HOST} '
                            cd ${ANSIBLE_WORKDIR}
                            
                            # Test inventory
                            if [ -f "inventory/hosts" ]; then
                                echo "Testing inventory file:"
                                ansible-inventory --list -i inventory/hosts || echo "Inventory test failed"
                            else
                                echo "Inventory file not found"
                            fi
                        '
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo 'All tests passed!'
        }
        failure {
            echo 'Some tests failed!'
        }
    }
}