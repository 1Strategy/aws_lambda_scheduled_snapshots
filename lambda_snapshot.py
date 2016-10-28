import boto3
import datetime

# This lambda function will create snapshots for all of the volumes for instances in
# a given region with a predetermined flag (in this case 'ShouldDailySnapshot')

__author__ = 'Justin Iravani'

ec2 = []

is_dry_run = False

# Tags to exclude from the snapshots
unwanted_tags = ['Name', 'ShouldSnapshotDaily']


def lambda_handler(event, context):

    region = event['region']
    snapshot_region(region)
    print('Success')


def snapshot_region(region):
    # Connects to ec2 in a region (provided by event argument)
    ec2 = boto3.resource('ec2', region_name=region)

    instances = ec2.instances.all()

    # For each instance in the region, see if it needs to be snapshotted
    for instance in instances:

        # If 'ShouldSnapshotDaily' tag with a Value of 'True'
        if should_snapshot(instance.tags):
            cleaned_tags = clean_tags(instance.tags, unwanted_tags)
            create_snapshot_with_tags(instance, cleaned_tags)


def create_snapshot_with_tags(instance, tags):
    volumes = instance.volumes.all()

    # For each volume for a given instance, create a snapshot
    for volume in volumes:
        try:
            # Create snapshot
            snapshot = volume.create_snapshot(DryRun=is_dry_run,
                                              VolumeId=volume.id,
                                              Description="auto generated snapshot from lambda")
            # Create 'Name' tag for the snapshot
            snapshot.create_tags(DryRun=is_dry_run,
                                 Tags=[{'Key': 'Name', 'Value': "snapshot-%s-%s-%s" % (
                                 instance.id, volume.id, datetime.datetime.now())}])

            # Mirror all tags from parent instance
            if tags:
                snapshot.create_tags(DryRun=is_dry_run, Tags=tags)

        except Exception as e:
            print(e.message)
            print("Error occured while creating a snapshot for volume %s ." % (volume.id))


def should_snapshot(tags):
    for tag in tags:
        if tag['Key'] == 'ShouldSnapshotDaily' and tag['Value'] == 'True':
            return True
    return False


def clean_tags(tags, unwanted_tags):
    # removes reserved (aws:*) and unwanted tags
    new_tags = []
    for tag in tags:
        if not tag.get('Key').startswith('aws:') \
                and tag.get('Key') not in unwanted_tags:
            new_tags.append(tag)
    return new_tags
