import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # Get all EBS snapshots owned by you
    response = ec2.describe_snapshots(OwnerIds=['self'])

    # Get all active EC2 instance IDs
    instances_response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    active_instance_ids = set()

    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            active_instance_ids.add(instance['InstanceId'])

    # Iterate through each snapshot
    for snapshot in response['Snapshots']:
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')

        # Case 1: Snapshot has no volume (orphan snapshot)
        if not volume_id:
            ec2.delete_snapshot(SnapshotId=snapshot_id)
            print(f"Deleted snapshot {snapshot_id} (no volume attached)")

        else:
            try:
                # Check if volume exists
                volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
                volume = volume_response['Volumes'][0]

                # Check if volume is attached to any active instance
                attached_instances = [
                    attachment['InstanceId']
                    for attachment in volume.get('Attachments', [])
                ]

                # If not attached to any running instance → delete snapshot
                if not any(instance_id in active_instance_ids for instance_id in attached_instances):
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted snapshot {snapshot_id} (unused volume)")

            except Exception as e:
                # Volume does not exist → delete snapshot
                print(f"Volume {volume_id} not found, deleting snapshot {snapshot_id}")
                ec2.delete_snapshot(SnapshotId=snapshot_id)

    return {
        "statusCode": 200,
        "body": "Snapshot cleanup completed"
    }
