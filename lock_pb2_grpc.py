# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import lock_pb2 as lock__pb2

GRPC_GENERATED_VERSION = '1.67.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in lock_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class LockServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.client_init = channel.unary_unary(
                '/lock_service.LockService/client_init',
                request_serializer=lock__pb2.Int.SerializeToString,
                response_deserializer=lock__pb2.Int.FromString,
                _registered_method=True)
        self.lock_acquire = channel.unary_unary(
                '/lock_service.LockService/lock_acquire',
                request_serializer=lock__pb2.lock_args.SerializeToString,
                response_deserializer=lock__pb2.Response.FromString,
                _registered_method=True)
        self.lock_release = channel.unary_unary(
                '/lock_service.LockService/lock_release',
                request_serializer=lock__pb2.lock_args.SerializeToString,
                response_deserializer=lock__pb2.Response.FromString,
                _registered_method=True)
        self.file_append = channel.unary_unary(
                '/lock_service.LockService/file_append',
                request_serializer=lock__pb2.file_args.SerializeToString,
                response_deserializer=lock__pb2.Response.FromString,
                _registered_method=True)
        self.client_close = channel.unary_unary(
                '/lock_service.LockService/client_close',
                request_serializer=lock__pb2.Int.SerializeToString,
                response_deserializer=lock__pb2.Int.FromString,
                _registered_method=True)


class LockServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def client_init(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def lock_acquire(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def lock_release(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def file_append(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def client_close(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_LockServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'client_init': grpc.unary_unary_rpc_method_handler(
                    servicer.client_init,
                    request_deserializer=lock__pb2.Int.FromString,
                    response_serializer=lock__pb2.Int.SerializeToString,
            ),
            'lock_acquire': grpc.unary_unary_rpc_method_handler(
                    servicer.lock_acquire,
                    request_deserializer=lock__pb2.lock_args.FromString,
                    response_serializer=lock__pb2.Response.SerializeToString,
            ),
            'lock_release': grpc.unary_unary_rpc_method_handler(
                    servicer.lock_release,
                    request_deserializer=lock__pb2.lock_args.FromString,
                    response_serializer=lock__pb2.Response.SerializeToString,
            ),
            'file_append': grpc.unary_unary_rpc_method_handler(
                    servicer.file_append,
                    request_deserializer=lock__pb2.file_args.FromString,
                    response_serializer=lock__pb2.Response.SerializeToString,
            ),
            'client_close': grpc.unary_unary_rpc_method_handler(
                    servicer.client_close,
                    request_deserializer=lock__pb2.Int.FromString,
                    response_serializer=lock__pb2.Int.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'lock_service.LockService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('lock_service.LockService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class LockService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def client_init(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/lock_service.LockService/client_init',
            lock__pb2.Int.SerializeToString,
            lock__pb2.Int.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def lock_acquire(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/lock_service.LockService/lock_acquire',
            lock__pb2.lock_args.SerializeToString,
            lock__pb2.Response.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def lock_release(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/lock_service.LockService/lock_release',
            lock__pb2.lock_args.SerializeToString,
            lock__pb2.Response.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def file_append(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/lock_service.LockService/file_append',
            lock__pb2.file_args.SerializeToString,
            lock__pb2.Response.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def client_close(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/lock_service.LockService/client_close',
            lock__pb2.Int.SerializeToString,
            lock__pb2.Int.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
